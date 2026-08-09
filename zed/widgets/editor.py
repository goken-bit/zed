import os
from collections import deque

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.core.text import Label as CoreLabel
from kivy.core.window import Keyboard, Window
from kivy.graphics import Color, InstructionGroup, Rectangle
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget

from zed.theme import Theme
from zed.widgets.syntax import Highlighter, language_for

KC = Keyboard.keycodes


class CodeEditor(ScrollView):
    def __init__(self, path=None, **kw):
        kw.setdefault("do_scroll_x", True)
        kw.setdefault("do_scroll_y", True)
        kw.setdefault("bar_width", 5)
        kw.setdefault("scroll_type", ["bars", "content"])
        kw.setdefault("scroll_timeout", 80)
        super().__init__(**kw)
        self.path = path
        self.language = None
        self.highlighter = Highlighter()
        self.text = ""
        self.cursor = (0, 0)
        self.anchor = None
        self.version = 0
        self._line_cache = None
        self._line_widths = None
        self._max_width = 0
        self._measure_cache = {}

        self.undo_stack = deque(maxlen=500)
        self.redo_stack = deque(maxlen=500)
        self._last_undo_at = None

        self.labels = {}
        self.content = None
        self._gutter = None
        self._caret_color = None
        self._caret_rect = None
        self._curline_rect = None
        self._sel_group = None
        self._blink_job = None
        self._anim_job = None
        self._caret_visible = True
        self._last_touch = None
        self.on_edit = None
        self.on_cursor = None
        self._cursor_job = None

        self.bind(scroll_y=self._on_scroll, scroll_x=self._on_scroll,
                  size=self._on_size)

        self._build_scene()
        if path and os.path.exists(path):
            self.open_file(path)

    def _build_scene(self):
        self.content = FloatLayoutScene(size_hint=(None, None), size=(1, 1))
        self.add_widget(self.content)
        self._gutter = None
        with self.content.canvas.before:
            Color(*Theme.current_line)
            self._curline_rect = Rectangle(size=(0, 0))
        self._sel_group = InstructionGroup()
        self.content.canvas.before.add(self._sel_group)
        with self.content.canvas:
            self._caret_color = Color(*Theme.caret)
            self._caret_rect = Rectangle(size=(2, Theme.line_height - 6))
        self._refresh_after()

    def _content_resized(self, *a):
        self._on_scroll()

    def open_file(self, path):
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
        except OSError:
            text = ""
        self.path = path
        self.language = language_for(path)
        self.highlighter.set_language(self.language)
        self.set_text(text)

    def set_text(self, text):
        self.text = text.replace("\r\n", "\n").replace("\r", "\n")
        self.version += 1
        self._line_cache = None
        self._line_widths = None
        self.cursor = (0, 0)
        self.anchor = None
        self._schedule_render()

    def lines(self):
        if self._line_cache is None:
            self._line_cache = self.text.split("\n")
        return self._line_cache

    def _offset(self, line, col):
        lines = self.lines()
        return sum(len(l) + 1 for l in lines[:line]) + col

    def _pos_of_offset(self, offset):
        lines = self.lines()
        acc = 0
        for i, l in enumerate(lines):
            if offset <= acc + len(l):
                return (i, offset - acc)
            acc += len(l) + 1
        return (len(lines) - 1, len(lines[-1]))

    def _measure(self, text):
        if not text:
            return 0
        if text in self._measure_cache:
            return self._measure_cache[text]
        lbl = CoreLabel(text=text, font_name=Theme.font_mono, font_size=Theme.font_size)
        lbl.refresh()
        w = lbl.size[0]
        if len(self._measure_cache) > 3000:
            self._measure_cache.clear()
        self._measure_cache[text] = w
        return w

    def _ensure_cache(self):
        if self._line_cache is not None and self._line_widths is not None:
            return
        self._line_widths = [self._measure(l) for l in self.lines()]
        self._max_width = max(self._line_widths) if self._line_widths else 0

    def _content_height(self):
        return len(self.lines()) * Theme.line_height + 14

    def _content_width(self):
        return max(self._max_width + 80, self.width)

    def _schedule_render(self):
        if self._anim_job:
            self._anim_job.cancel()
        self._anim_job = Clock.schedule_once(self._do_render, 0.02)

    def _do_render(self, dt=None):
        self._anim_job = None
        self._refresh_after()

    def _refresh_after(self):
        if self.content is None:
            return
        self._ensure_cache()
        self.content.size = (self._content_width(), self._content_height())
        self._update_visible()
        self._update_caret()
        if self._gutter is not None:
            self._gutter.update(self)

    def _visible_range(self):
        view_h = self.height
        content_h = self.content.height
        scroll_top = self.scroll_y * (content_h - view_h) if content_h > view_h else 0
        start = int(scroll_top // Theme.line_height)
        end = int((scroll_top + view_h) // Theme.line_height) + 2
        total = len(self.lines())
        return max(0, start), min(end, total)

    def _update_visible(self):
        if self.content is None:
            return
        self._ensure_cache()
        content_h = self.content.height
        view_h = self.height
        top = self.scroll_y * (content_h - view_h) if content_h > view_h else 0
        start, end = self._visible_range()
        markup = self.highlighter.lines_for(self.text, self.version)
        total = len(self.lines())

        for idx in list(self.labels):
            if idx < start or idx >= end:
                lbl = self.labels.pop(idx)
                self.content.remove_widget(lbl)

        for idx in range(start, end):
            lbl = self.labels.get(idx)
            if lbl is None:
                lbl = Label(markup=True, font_name=Theme.font_mono,
                            font_size=Theme.font_size, color=(1, 1, 1, 1),
                            size_hint=(None, None), halign="left", valign="middle",
                            text_size=(None, Theme.line_height))
                self.content.add_widget(lbl)
                self.labels[idx] = lbl
            lbl.text = markup[idx] if idx < len(markup) else ""
            lbl.width = self.content.width
            lbl.height = Theme.line_height
            lbl.x = 0
            lbl.y = content_h - (idx + 1) * Theme.line_height

    def _scroll_top(self):
        view_h = self.height
        content_h = self.content.height
        if content_h <= view_h:
            return 0
        return self.scroll_y * (content_h - view_h)

    def _scroll_left(self):
        cw = self.content.width
        if cw <= self.width:
            return 0
        return self.scroll_x * (cw - self.width)

    def _on_scroll(self, *a):
        if self.content is None:
            return
        self._update_visible()
        self._update_caret()
        if self._gutter is not None:
            self._gutter.update(self)

    def _on_size(self, *a):
        if self.content is not None:
            Clock.schedule_once(lambda dt: self._refresh_after(), -1)

    def _selection_lines(self):
        if not self.anchor or self.anchor == self.cursor:
            return []
        a, b = self._sel_order()
        lines = self.lines()
        out = []
        for li in range(a[0], min(b[0], len(lines) - 1) + 1):
            s = a[1] if li == a[0] else 0
            e = b[1] if li == b[0] else len(lines[li])
            out.append((li, s, e))
        return out

    def _draw_selection(self):
        self._sel_group.clear()
        if not self.anchor or self.anchor == self.cursor:
            return
        content_h = self.content.height
        for (li, s, e) in self._selection_lines():
            y = content_h - (li + 1) * Theme.line_height
            x = self._measure(self.lines()[li][:s])
            w = self._measure(self.lines()[li][s:e])
            self._sel_group.add(Color(*Theme.selection_bg))
            self._sel_group.add(Rectangle(pos=(x, y), size=(max(1, w), Theme.line_height)))

    def _update_caret(self):
        if self.content is None:
            return
        self._draw_selection()
        lines = self.lines()
        line, col = self.cursor
        if not lines:
            line = col = 0
        else:
            line = max(0, min(line, len(lines) - 1))
            col = max(0, min(col, len(lines[line])))
        content_h = self.content.height
        x = self._measure(lines[line][:col]) if lines else 0
        y = content_h - (line + 1) * Theme.line_height
        self._caret_rect.pos = (x, y + 3)
        self._curline_rect.pos = (0, y)
        self._curline_rect.size = (self.content.width, Theme.line_height)
        self._schedule_blink()
        if self.on_cursor:
            if self._cursor_job:
                self._cursor_job.cancel()
            self._cursor_job = Clock.schedule_once(lambda dt: self.on_cursor(), 0.05)

    def _schedule_blink(self):
        if self._blink_job:
            self._blink_job.cancel()
        self._blink_job = Clock.schedule_once(self._blink, 0.6)

    def _blink(self, *a):
        self._blink_job = None
        if self._caret_visible:
            self._caret_visible = False
            Animation(self._caret_color, rgba=(*Theme.caret[:3], 0.0),
                      duration=0.2).start(self._caret_color)
        else:
            self._caret_visible = True
            Animation(self._caret_color, rgba=(*Theme.caret[:3], 1.0),
                      duration=0.16).start(self._caret_color)
        self._blink_job = Clock.schedule_once(self._blink, 0.7)

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)
        res = super().on_touch_down(touch)
        self._last_touch = touch
        return res

    def on_touch_up(self, touch):
        if touch is self._last_touch and touch.grab_current is not None:
            moved = abs(touch.dx) + abs(touch.dy) > 8
            if not moved:
                self._set_cursor_from_touch(touch.pos)
                self.focus()
        return super().on_touch_up(touch)

    def _set_cursor_from_touch(self, pos):
        lines = self.lines()
        if not lines:
            self.cursor = (0, 0)
            return
        top = self._scroll_top()
        scroll_left = self._scroll_left()
        raw_line = int((top + (self.height - pos[1])) // Theme.line_height)
        line = max(0, min(raw_line, len(lines) - 1))
        x = pos[0] + scroll_left
        lo, hi = 0, len(lines[line])
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if self._measure(lines[line][:mid]) <= x:
                lo = mid
            else:
                hi = mid - 1
        col = lo
        half = self._measure(lines[line][col:col + 1]) / 2
        if self._measure(lines[line][:col]) + half < x and col < len(lines[line]):
            col += 1
        self.cursor = (line, col)
        self.anchor = None
        self._update_caret()

    def focus(self):
        try:
            Window.request_keyboard(self._keyboard_closed, self, "text")
        except Exception:
            pass

    def _keyboard_closed(self):
        pass

    def on_key(self, key, scancode, codepoint, modifiers):
        if key == KC["backspace"]:
            self.delete_back()
            return True
        if key == KC["delete"]:
            self.delete_forward()
            return True
        if key == KC["tab"]:
            self.type_indent()
            return True
        if key == KC["enter"]:
            self.type_newline()
            return True
        if key in (KC["left"], KC["right"], KC["up"], KC["down"]):
            self.move_cursor(key, modifiers)
            return True
        if key == KC["home"]:
            self.move_home(modifiers)
            return True
        if key == KC["end"]:
            self.move_end(modifiers)
            return True
        if key == KC["pageup"]:
            self.move_page(-1, modifiers)
            return True
        if key == KC["pagedown"]:
            self.move_page(1, modifiers)
            return True
        if key == KC["escape"]:
            return False
        return False

    def on_text_input(self, text):
        if not text or text in ("\t", "\r", "\n"):
            return False
        self.type_text(text)
        return True

    def on_ctrl_key(self, key, scancode, codepoint, modifiers):
        if key == KC["z"] and "shift" not in modifiers:
            self.undo()
            return True
        if key == KC["z"] and "shift" in modifiers:
            self.redo()
            return True
        if key == KC["y"]:
            self.redo()
            return True
        if key == KC["a"]:
            self.select_all()
            return True
        if key == KC["c"]:
            self.copy()
            return True
        if key == KC["x"]:
            self.cut()
            return True
        if key == KC["v"]:
            self.paste()
            return True
        if key == KC["s"]:
            if self.path:
                self.save()
            return "save"
        return False

    def type_text(self, text):
        line, col = self.cursor
        if self.anchor and self.anchor != self.cursor:
            self.delete_range(*self._sel_order())
            line, col = self.cursor
        self._snapshot_undo()
        off = self._offset(line, col)
        self.text = self.text[:off] + text + self.text[off:]
        self._line_cache = None
        self._line_widths = None
        self.version += 1
        self.cursor = (line, col + len(text))
        self.anchor = None
        if Theme.anim_enabled:
            self._animate_char(text, line, col)
        else:
            self._schedule_render()
        self._after_edit()

    def type_newline(self):
        line, col = self.cursor
        if self.anchor and self.anchor != self.cursor:
            self.delete_range(*self._sel_order())
            line, col = self.cursor
        l = self.lines()[line] if line < len(self.lines()) else ""
        indent = l[:len(l) - len(l.lstrip())]
        stripped = l.strip()
        if self.language is not None and stripped.endswith(":") and not l.rstrip().endswith("\\"):
            indent += " " * Theme.tab_width
        self._snapshot_undo()
        off = self._offset(line, col)
        self.text = self.text[:off] + "\n" + indent + self.text[off:]
        self._line_cache = None
        self._line_widths = None
        self.version += 1
        self.cursor = (line + 1, len(indent))
        self.anchor = None
        self._schedule_render()
        self._after_edit()

    def type_indent(self):
        if self.anchor and self.anchor != self.cursor:
            self.indent_selection()
            return
        self.type_text(" " * Theme.tab_width)

    def indent_selection(self):
        a, b = self._sel_order()
        lines = self.lines()
        start = a[0]
        end = b[0]
        if b[1] == 0 and end > start:
            end -= 1
        pad = " " * Theme.tab_width
        new_lines = []
        for i, l in enumerate(lines):
            new_lines.append(pad + l if start <= i <= end else l)
        self._snapshot_undo()
        self.text = "\n".join(new_lines)
        self._line_cache = None
        self._line_widths = None
        self.version += 1
        self.anchor = (start, a[1] + len(pad))
        self.cursor = (end, b[1] + len(pad))
        self._schedule_render()
        self._after_edit()

    def delete_back(self):
        if self.anchor and self.anchor != self.cursor:
            self.delete_range(*self._sel_order())
            self._after_edit()
            return
        line, col = self.cursor
        if col > 0:
            self.delete_range((line, col - 1), (line, col))
        elif line > 0:
            prev_len = len(self.lines()[line - 1])
            self.delete_range((line - 1, prev_len), (line, 0))
        self._after_edit()

    def delete_forward(self):
        if self.anchor and self.anchor != self.cursor:
            self.delete_range(*self._sel_order())
            self._after_edit()
            return
        line, col = self.cursor
        lines = self.lines()
        if col < len(lines[line]):
            self.delete_range((line, col), (line, col + 1))
        elif line < len(lines) - 1:
            self.delete_range((line, col), (line + 1, 0))
        self._after_edit()

    def delete_range(self, start, end):
        s = self._offset(*start)
        e = self._offset(*end)
        if s == e:
            return
        self._snapshot_undo()
        self.text = self.text[:s] + self.text[e:]
        self._line_cache = None
        self._line_widths = None
        self.version += 1
        self.cursor = self._pos_of_offset(s)
        self.anchor = None
        self._schedule_render()

    def _snapshot_undo(self):
        now = Clock.get_time()
        if self._last_undo_at is not None and now - self._last_undo_at < 0.6:
            return
        self.undo_stack.append((self.text, self.cursor))
        self._last_undo_at = now
        self.redo_stack.clear()

    def undo(self):
        if not self.undo_stack:
            return
        self.redo_stack.append((self.text, self.cursor))
        self.text, self.cursor = self.undo_stack.pop()
        self._line_cache = None
        self._line_widths = None
        self.version += 1
        self.anchor = None
        self._last_undo_at = Clock.get_time()
        self._schedule_render()
        self._after_edit()

    def redo(self):
        if not self.redo_stack:
            return
        self.undo_stack.append((self.text, self.cursor))
        self.text, self.cursor = self.redo_stack.pop()
        self._line_cache = None
        self._line_widths = None
        self.version += 1
        self.anchor = None
        self._last_undo_at = Clock.get_time()
        self._schedule_render()
        self._after_edit()

    def select_all(self):
        lines = self.lines()
        self.anchor = (0, 0)
        self.cursor = (max(0, len(lines) - 1), len(lines[-1]))
        self._update_caret()

    def copy(self):
        sel = self.selected_text()
        if sel:
            self._clip_copy(sel)

    def cut(self):
        sel = self.selected_text()
        if sel:
            self._clip_copy(sel)
            self.delete_range(*self._sel_order())
            self._after_edit()

    def paste(self):
        text = self._clip_paste()
        if text:
            self.type_multi(text)

    def type_multi(self, text):
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        line, col = self.cursor
        if self.anchor and self.anchor != self.cursor:
            self.delete_range(*self._sel_order())
            line, col = self.cursor
        self._snapshot_undo()
        off = self._offset(line, col)
        self.text = self.text[:off] + text + self.text[off:]
        self._line_cache = None
        self._line_widths = None
        self.version += 1
        nl = text.count("\n")
        if nl:
            lines = self.lines()
            self.cursor = (line + nl, len(lines[line + nl]))
        else:
            self.cursor = (line, col + len(text))
        self.anchor = None
        self._schedule_render()
        self._after_edit()

    def _clip_copy(self, text):
        try:
            from kivy.core.clipboard import Clipboard
            Clipboard.copy(text)
        except Exception:
            pass

    def _clip_paste(self):
        try:
            from kivy.core.clipboard import Clipboard
            return Clipboard.paste()
        except Exception:
            return ""

    def _sel_order(self):
        a, b = self.anchor, self.cursor
        if a[0] < b[0] or (a[0] == b[0] and a[1] < b[1]):
            return a, b
        return b, a

    def selected_text(self):
        if not self.anchor or self.anchor == self.cursor:
            return ""
        a, b = self._sel_order()
        return self.text[self._offset(*a):self._offset(*b)]

    def move_cursor(self, key, modifiers):
        line, col = self.cursor
        lines = self.lines()
        prev = (line, col)
        if key == KC["left"]:
            if col > 0:
                col -= 1
            elif line > 0:
                line -= 1
                col = len(lines[line])
        elif key == KC["right"]:
            if col < len(lines[line]):
                col += 1
            elif line < len(lines) - 1:
                line += 1
                col = 0
        elif key == KC["up"]:
            line = max(0, line - 1)
            col = min(col, len(lines[line]))
        elif key == KC["down"]:
            line = min(len(lines) - 1, line + 1)
            col = min(col, len(lines[line]))
        if "shift" in modifiers:
            if self.anchor is None:
                self.anchor = prev
        else:
            self.anchor = None
        self.cursor = (line, col)
        self._ensure_visible()
        self._update_caret()

    def move_home(self, modifiers):
        line, col = self.cursor
        l = self.lines()[line]
        indent = len(l) - len(l.lstrip(" "))
        target = indent if col > indent else 0
        prev = (line, col)
        self.cursor = (line, target)
        if "shift" in modifiers:
            if self.anchor is None:
                self.anchor = prev
        else:
            self.anchor = None
        self._ensure_visible()
        self._update_caret()

    def move_end(self, modifiers):
        line, col = self.cursor
        prev = (line, col)
        self.cursor = (line, len(self.lines()[line]))
        if "shift" in modifiers:
            if self.anchor is None:
                self.anchor = prev
        else:
            self.anchor = None
        self._ensure_visible()
        self._update_caret()

    def move_page(self, direction, modifiers):
        line, col = self.cursor
        lines = self.lines()
        delta = max(1, int(self.height // Theme.line_height) - 1) * direction
        line = max(0, min(len(lines) - 1, line + delta))
        col = min(col, len(lines[line]))
        self.cursor = (line, col)
        if "shift" not in modifiers:
            self.anchor = None
        self._ensure_visible()
        self._update_caret()

    def _ensure_visible(self):
        line, _ = self.cursor
        view_h = self.height
        content_h = self.content.height
        top = self._scroll_top()
        y_top = line * Theme.line_height
        if y_top < top:
            self._set_scroll_y((y_top) / max(1, content_h - view_h))
        elif y_top + Theme.line_height > top + view_h:
            self._set_scroll_y((y_top + Theme.line_height - view_h) / max(1, content_h - view_h))

    def _set_scroll_y(self, v):
        self.scroll_y = min(1.0, max(0.0, v))
        self._on_scroll()

    def _after_edit(self):
        if self._blink_job:
            self._blink_job.cancel()
        self._caret_visible = True
        self._caret_color.rgba = (*Theme.caret[:3], 1.0)
        self._schedule_blink()
        if self.on_edit:
            self.on_edit()

    def _animate_char(self, text, line, col):
        self._ensure_cache()
        content_h = self.content.height
        x = self._measure(self.lines()[line][:col])
        y = content_h - (line + 1) * Theme.line_height
        glyph = Label(text=text, font_name=Theme.font_mono, font_size=Theme.font_size,
                      color=(1, 1, 1, 1), size_hint=(None, None),
                      halign="center", valign="middle",
                      text_size=(None, Theme.line_height))
        glyph.size = (Theme.font_size + 6, Theme.line_height)
        glyph.pos = (x, y)
        self.content.add_widget(glyph)
        dur = 0.16
        style = Theme.typing_style
        if style == "glow":
            with glyph.canvas.before:
                c = Color(*Theme.accent_light[:3], 0.6)
                gl = Rectangle(pos=glyph.pos, size=glyph.size)
            glyph.bind(pos=lambda *_: setattr(gl, "pos", glyph.pos))
            anim = Animation(color=(1, 1, 1, 1), duration=dur)
            Clock.schedule_once(
                lambda dt: Animation(rgba=(*Theme.accent_light[:3], 0.0),
                                     duration=0.24).start(c), dur)
        elif style == "type":
            glyph.opacity = 0
            glyph.y = y + Theme.line_height * 0.7
            anim = Animation(opacity=1, y=y, duration=0.2, t="out_back")
        else:
            glyph.opacity = 0
            glyph.font_size = Theme.font_size * 1.45
            anim = Animation(font_size=Theme.font_size, opacity=1,
                             duration=dur, t="out_cubic")
        anim.bind(on_complete=lambda *_: self._remove_glyph(glyph))
        anim.start(glyph)
        self._schedule_commit(dur + 0.06)

    def _remove_glyph(self, glyph):
        if glyph.parent:
            glyph.parent.remove_widget(glyph)

    def _schedule_commit(self, delay):
        if self._anim_job:
            self._anim_job.cancel()
        self._anim_job = Clock.schedule_once(self._do_render, delay)

    def save(self):
        if not self.path:
            return False
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                f.write(self.text)
            return True
        except OSError:
            return False


class FloatLayoutScene(Widget):
    pass


class Gutter(Widget):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.size_hint = (None, 1.0)
        self.width = 3 * Theme.font_size + Theme.gutter_pad

    def update(self, editor):
        self.canvas.clear()
        top = editor._scroll_top()
        start, end = editor._visible_range()
        total = len(editor.lines())
        with self.canvas:
            Color(*Theme.bg_alt)
            Rectangle(pos=(0, 0), size=(self.width, self.height))
            Color(1, 1, 1, 0.12)
            Rectangle(pos=(self.width - 1, 0), size=(1, self.height))
            Color(0.55, 0.55, 0.58, 1)
            for idx in range(start, min(end, total)):
                y = editor.height - (idx * Theme.line_height - top + Theme.line_height)
                num = str(idx + 1)
                lbl = CoreLabel(text=num, font_name=Theme.font_mono,
                                font_size=Theme.font_size - 1)
                lbl.refresh()
                tex = lbl.texture
                ts = tex.size
                tx = self.width - Theme.gutter_pad - ts[0]
                ty = y + (Theme.line_height - ts[1]) / 2
                Rectangle(pos=(tx, ty), size=ts, texture=tex)
