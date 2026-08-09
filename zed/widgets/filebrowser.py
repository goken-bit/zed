import os

from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput

from zed.theme import Theme
from zed.widgets.base import AnimatedButton, Hoverable, IconButton
from zed.widgets.modal import Modal


class BrowserRow(Hoverable):
    def __init__(self, browser, path, name, is_dir, **kw):
        super().__init__(**kw)
        self.browser = browser
        self.path = path
        self.name = name
        self.is_dir = is_dir
        self.size_hint = (1, None)
        self.height = 30
        self.normal_color = (0, 0, 0, 0)
        self.hover_color = (1, 1, 1, 0.06)
        self.background_normal = ""
        self.background_down = ""
        self.border = (0, 0, 0, 0)
        box = BoxLayout(size_hint=(1, 1), spacing=8, padding=(10, 0, 10, 0))
        glyph = Label(text="\u25a6" if is_dir else "\u25a5", font_name=Theme.font_ui,
                      font_size=12, color=Theme.fg_faint, size_hint=(None, 1), width=18,
                      valign="middle", halign="center")
        self.name_lbl = Label(text=name, font_name=Theme.font_ui, font_size=13,
                              color=Theme.fg if is_dir else Theme.fg_dim,
                              size_hint=(1, 1), halign="left", valign="middle",
                              shorten=True, max_lines=1)
        box.add_widget(glyph)
        box.add_widget(self.name_lbl)
        self.add_widget(box)

    def on_release(self):
        self.browser.select(self)


class FileBrowser(Modal):
    def __init__(self, app, mode="file", title="Open File", **kw):
        super().__init__(**kw)
        self.app = app
        self.mode = mode
        self.current = ""
        self.selected = None
        self._build_panel(title)

    def _build_panel(self, title):
        self.panel = BoxLayout(orientation="vertical", size_hint=(None, None),
                               size=(min(560, self.width * 0.9),
                                     min(520, self.height * 0.8)),
                               spacing=0)
        with self.panel.canvas.before:
            Color(*Theme.bg_panel)
            self._bg = Rectangle()
            Color(1, 1, 1, 0.12)
            self._border = Rectangle(size=(2, 2))
        self.panel.bind(pos=self._draw, size=self._draw)

        header = BoxLayout(size_hint=(1, None), height=44, padding=(14, 0, 8, 0))
        header.add_widget(Label(text=title, font_name=Theme.font_ui, font_size=14,
                                color=Theme.fg, halign="left", valign="middle"))
        header.add_widget(IconButton(text="\u2715", font_size=13, size=(28, 28),
                                     on_press=self.close))
        self.panel.add_widget(header)

        nav = BoxLayout(size_hint=(1, None), height=40, padding=(12, 4, 12, 4),
                        spacing=6)
        self.path_input = TextInput(multiline=False, font_name=Theme.font_ui,
                                    font_size=12, foreground_color=Theme.fg,
                                    background_color=Theme.bg_input,
                                    cursor_color=Theme.caret, padding=(10, 8))
        self.path_input.bind(on_text_validate=lambda *_: self.go(self.path_input.text))
        nav.add_widget(self.path_input)
        nav.add_widget(IconButton(text="\u2191", font_size=14, size=(32, 30),
                                  on_press=self.up))
        nav.add_widget(AnimatedButton(text="Go", size=(46, 30), font_size=12,
                                      on_press=lambda: self.go(self.path_input.text)))
        self.panel.add_widget(nav)

        body = ScrollView(bar_width=5)
        self.list = BoxLayout(orientation="vertical", size_hint_y=None,
                              spacing=0, padding=(4, 4))
        self.list.bind(minimum_height=self.list.setter("height"))
        body.add_widget(self.list)
        self.panel.add_widget(body)

        footer = BoxLayout(size_hint=(1, None), height=48, padding=(12, 6, 12, 6),
                           spacing=6)
        footer.add_widget(BoxLayout())
        self.open_btn = AnimatedButton(text="Open", accent=True, size=(92, 32),
                                       font_size=13, on_press=self.confirm)
        footer.add_widget(AnimatedButton(text="Cancel", size=(92, 32), font_size=13,
                                         on_press=self.close))
        footer.add_widget(self.open_btn)
        self.panel.add_widget(footer)

        self.add_widget(self.panel)
        self._draw()
        if self.mode == "folder":
            self.open_btn.text = "Open Folder"
        if os.path.isdir(self.app.workdir):
            self.go(self.app.workdir)

    def _draw(self, *a):
        self._bg.pos = self.panel.pos
        self._bg.size = self.panel.size
        self._border.pos = self.panel.pos
        self._border.size = self.panel.size

    def _panel_y(self):
        return max(6, (self.height - self.panel.height) / 2)

    def go(self, path):
        path = os.path.expanduser(path or "")
        if os.path.isfile(path):
            if self.mode == "file":
                self.selected = path
                self.current = os.path.dirname(path)
                self.path_input.text = path
            else:
                self.go(os.path.dirname(path))
            return
        if not os.path.isdir(path):
            self.app.toasts.toast("Not a folder", "error")
            return
        self.current = path
        self.path_input.text = path
        self.selected = None
        self._fill()

    def up(self):
        parent = os.path.dirname(self.current)
        if parent and parent != self.current:
            self.go(parent)

    def _fill(self):
        self.list.clear_widgets()
        try:
            items = sorted(os.scandir(self.current),
                           key=lambda e: (not e.is_dir(), e.name.lower()))
        except OSError:
            items = []
        for e in items:
            self.list.add_widget(BrowserRow(self, e.path, e.name, e.is_dir()))

    def select(self, row):
        self.selected = row.path if not row.is_dir else None
        if row.is_dir:
            self.go(row.path)
        else:
            self.path_input.text = row.path

    def confirm(self):
        if self.mode == "folder":
            if os.path.isdir(self.current):
                self.app.set_root(self.current)
            self.close()
            return
        if self.selected:
            self.app.open_file(self.selected)
            self.close()


class PromptDialog(Modal):
    def __init__(self, app, title, hint, action_label, on_done, **kw):
        super().__init__(**kw)
        self.app = app
        self.on_done = on_done
        self._build(title, hint, action_label)

    def _build(self, title, hint, action_label):
        self.panel = BoxLayout(orientation="vertical", size_hint=(None, None),
                               size=(360, 190), spacing=0)
        with self.panel.canvas.before:
            Color(*Theme.bg_panel)
            self._bg = Rectangle()
        self.panel.bind(pos=self._draw, size=self._draw)
        header = BoxLayout(size_hint=(1, None), height=44, padding=(14, 0, 8, 0))
        header.add_widget(Label(text=title, font_name=Theme.font_ui, font_size=14,
                                color=Theme.fg, halign="left", valign="middle"))
        self.panel.add_widget(header)
        self.input = TextInput(multiline=False, font_name=Theme.font_ui, font_size=13,
                               foreground_color=Theme.fg, background_color=Theme.bg_input,
                               cursor_color=Theme.caret, padding=(10, 10),
                               hint_text=hint, hint_text_color=Theme.fg_faint,
                               size_hint=(1, None), height=40)
        self.panel.add_widget(BoxLayout(size_hint=(1, None), height=8))
        self.panel.add_widget(BoxLayout(size_hint=(1, None), height=44,
                                        padding=(14, 0, 14, 0),
                                        children=[self.input]))
        self.panel.add_widget(BoxLayout(size_hint=(1, None), height=4))
        footer = BoxLayout(size_hint=(1, None), height=48, padding=(14, 6, 14, 6),
                           spacing=6)
        footer.add_widget(BoxLayout())
        footer.add_widget(AnimatedButton(text="Cancel", size=(92, 32), font_size=13,
                                         on_press=self.close))
        self.ok = AnimatedButton(text=action_label, accent=True, size=(92, 32),
                                 font_size=13, on_press=self._ok)
        footer.add_widget(self.ok)
        self.panel.add_widget(footer)
        self.add_widget(self.panel)
        self._draw()

    def _draw(self, *a):
        self._bg.pos = self.panel.pos
        self._bg.size = self.panel.size

    def _panel_y(self):
        return max(6, (self.height - self.panel.height) / 2)

    def _ok(self):
        value = self.input.text.strip()
        if not value:
            return
        self.close()
        self.on_done(value)
