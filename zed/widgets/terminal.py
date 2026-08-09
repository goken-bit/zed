from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput

from zed.theme import Theme
from zed.widgets.base import AnimatedButton

ANSI_COLORS = {
    "30": "#3b3b3b", "31": "#e06c75", "32": "#98c379", "33": "#d19a66",
    "34": "#61afef", "35": "#c678dd", "36": "#56b6c2", "37": "#dcdfe4",
    "90": "#5c5c5c", "91": "#f44747", "92": "#b5cea8", "93": "#e2c08d",
    "94": "#6db1f7", "95": "#d2a3e8", "96": "#7fd4dd", "97": "#ffffff",
}


def ansi_to_markup(text):
    runs = []
    buf = []
    color = None
    bold = False
    i = 0
    n = len(text)

    def flush():
        if buf:
            runs.append(("".join(buf), color, bold))
            buf.clear()

    while i < n:
        c = text[i]
        if c == "\x1b" and i + 1 < n and text[i + 1] == "[":
            j = text.find("m", i + 2)
            if j == -1:
                buf.append(c)
                i += 1
                continue
            flush()
            for p in text[i + 2:j].split(";"):
                if not p:
                    p = "0"
                if p == "0":
                    color = None
                    bold = False
                elif p == "1":
                    bold = True
                elif p in ANSI_COLORS:
                    color = ANSI_COLORS[p]
            i = j + 1
            continue
        buf.append(c)
        i += 1
    flush()

    out = []
    for seg, col, b in runs:
        esc = seg.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        esc = esc.replace("[", "&#91;").replace("]", "&#93;")
        if b and col:
            out.append("[b][color=#%s]%s[/color][/b]" % (col, esc))
        elif col:
            out.append("[color=#%s]%s[/color]" % (col, esc))
        elif b:
            out.append("[b]%s[/b]" % esc)
        else:
            out.append(esc)
    return "".join(out)


class Terminal(BoxLayout):
    def __init__(self, app, **kw):
        kw.setdefault("orientation", "vertical")
        kw.setdefault("spacing", 0)
        super().__init__(**kw)
        self.app = app
        self._running = False
        self._build()

    def _build(self):
        with self.canvas.before:
            Color(*Theme.bg_panel)
            self._bg = Rectangle()
        self.bind(pos=self._draw, size=self._draw)

        header = BoxLayout(size_hint=(1, None), height=40, padding=(8, 6),
                           spacing=6)
        self.title = Label(text="OUTPUT", font_name=Theme.font_ui, font_size=11,
                           color=Theme.fg_faint, size_hint=(None, 1), halign="left",
                           valign="middle", width=70)
        self.lang_badge = Label(text="", font_name=Theme.font_ui, font_size=11,
                                color=Theme.accent_light, size_hint=(None, 1),
                                valign="middle", width=120)
        header.add_widget(self.title)
        header.add_widget(self.lang_badge)
        header.add_widget(BoxLayout())
        self.run_btn = AnimatedButton(text="\u25b6  Run", accent=True, on_press=self._on_run,
                                      size=(92, 28), font_size=12)
        self.stop_btn = AnimatedButton(text="\u25a0  Stop", on_press=self._on_stop,
                                       size=(92, 28), font_size=12)
        self.clear_btn = AnimatedButton(text="Clear", on_press=self.clear,
                                        size=(70, 28), font_size=12)
        header.add_widget(self.run_btn)
        header.add_widget(self.stop_btn)
        header.add_widget(self.clear_btn)

        body = ScrollView(bar_width=6)
        self.lines_box = BoxLayout(size_hint_y=None, orientation="vertical",
                                   spacing=0, padding=(10, 6, 10, 6))
        self.lines_box.bind(minimum_height=self.lines_box.setter("height"))
        body.add_widget(self.lines_box)
        self._body = body

        self.input = TextInput(
            multiline=False, size_hint=(1, None), height=30,
            font_name=Theme.font_mono, font_size=13,
            foreground_color=Theme.fg, cursor_color=Theme.caret,
            background_color=Theme.bg_input, border=(1, 1, 1, 1),
            padding=(10, 6), hint_text="  \u203a  type input\u2026",
            hint_text_color=Theme.fg_faint,
        )
        self.input.bind(on_text_validate=self._send_input)

        self.add_widget(header)
        self.add_widget(body)
        self.add_widget(self.input)

    def _draw(self, *a):
        self._bg.pos = self.pos
        self._bg.size = self.size

    def write(self, text, color=None):
        markup = ansi_to_markup(text)
        if color:
            markup = "[color=#%s]%s[/color]" % (color, markup)
        chunk = Label(text=markup, markup=True, font_name=Theme.font_mono,
                      font_size=12.5, color=Theme.fg, size_hint_y=None,
                      halign="left", valign="top", padding=(0, 1),
                      text_size=(None, None))
        chunk.bind(texture_size=lambda *_: self._sized(chunk))
        self.lines_box.add_widget(chunk)
        self._autoscroll()

    def _sized(self, chunk):
        if chunk.height < 1:
            chunk.height = chunk.texture_size[1] if chunk.texture_size[1] else 16
            chunk.width = max(10, self._body.width - 40)
            chunk.text_size = (chunk.width, None)

    def _autoscroll(self):
        Clock.schedule_once(lambda dt: setattr(self._body, "scroll_y", 0), 0.02)

    def clear(self, *a):
        self.lines_box.clear_widgets()

    def set_language(self, lang_name):
        self.lang_badge.text = lang_name or ""

    def _on_run(self):
        if self.app and not self._running:
            self.app.run_active()

    def _on_stop(self):
        if self.app:
            self.app.stop_run()

    def _send_input(self, *a):
        if self.app:
            self.app.send_run_input(self.input.text)
            self.input.text = ""

    def on_run_start(self, lang_name):
        self._running = True
        self.stop_btn.base_color = [0.32, 0.12, 0.12, 1.0]
        self.clear()
        self.write("[\u2500 running %s \u2500]\n" % (lang_name or "script"), "6e6e6e")
        self.set_language(lang_name)

    def on_run_done(self, rc, elapsed=None):
        self._running = False
        self.stop_btn.base_color = [0.16, 0.16, 0.17, 1.0]
        if rc == 0:
            self.write("\n[\u2713 exited 0%s]\n" % (" in %.2fs" % elapsed if elapsed else ""), "4ec9b0")
        else:
            self.write("\n[\u2717 exited %d%s]\n" % (rc, " in %.2fs" % elapsed if elapsed else ""), "f44747")

    def on_line(self, text):
        self.write(text)
