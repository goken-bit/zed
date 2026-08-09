import os

from kivy.animation import Animation
from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView

from zed.theme import Theme
from zed.widgets.base import Hoverable


class FileRow(Hoverable):
    def __init__(self, tree, path, name, is_dir, depth, **kw):
        super().__init__(**kw)
        self.tree = tree
        self.path = path
        self.name = name
        self.is_dir = is_dir
        self.depth = depth
        self.size_hint = (1, None)
        self.height = 28
        self.normal_color = (0, 0, 0, 0)
        self.hover_color = (1, 1, 1, 0.05)
        self.background_normal = ""
        self.background_down = ""
        self.border = (0, 0, 0, 0)
        self.bind(size=self._draw, pos=self._draw)
        with self.canvas.before:
            self._bg_color = Color(0, 0, 0, 0)
            self._bg = Rectangle()
            Color(*Theme.accent)
            self._bar = Rectangle(size=(2, 0))

        box = BoxLayout(size_hint=(1, 1), spacing=4, padding=(4, 0, 4, 0))
        self._indent = BoxLayout(size_hint=(None, 1), width=self.depth * 14)
        chev = Label(text="\u25b8" if is_dir else "", font_name=Theme.font_ui,
                     font_size=10, color=Theme.fg_faint, size_hint=(None, 1), width=16,
                     valign="middle", halign="center")
        glyph = Label(text="\u25a6" if is_dir else "\u25a5", font_name=Theme.font_ui,
                      font_size=11, color=Theme.fg_faint, size_hint=(None, 1), width=16,
                      valign="middle", halign="center")
        self.name_lbl = Label(text=name, font_name=Theme.font_ui, font_size=13,
                              color=Theme.fg_dim, size_hint=(1, 1), halign="left",
                              valign="middle", shorten=True, max_lines=1)
        self.name_lbl.bind(size=lambda *a: setattr(self.name_lbl, "text_size",
                                                   (self.name_lbl.width, None)))
        self.bind(hovered=self._on_hover_state)
        self.chev = chev
        box.add_widget(self._indent)
        box.add_widget(chev)
        box.add_widget(glyph)
        box.add_widget(self.name_lbl)
        self.add_widget(box)
        self._draw()

    def _draw(self, *a):
        self._bg.pos = self.pos
        self._bg.size = self.size
        if self.tree.active_path == self.path:
            self._bg_color.rgba = Theme.bg_active
            self._bar.size = (2, self.height)
            self._bar.pos = (self.x, self.y)
            self.name_lbl.color = Theme.accent_light
        else:
            self._bg_color.rgba = (0, 0, 0, 0)
            self._bar.size = (2, 0)
            self.name_lbl.color = Theme.fg if self.is_dir else Theme.fg_dim

    def _on_hover_state(self, *a):
        if self.tree.active_path == self.path:
            return
        target = (1, 1, 1, 0.06) if self.hovered else (0, 0, 0, 0)
        Animation(rgba=target, duration=0.15, t="out_cubic").start(self._bg_color)

    def on_release(self):
        self.tree.on_row_click(self)

    def set_expanded(self, expanded):
        self.chev.text = "\u25be" if expanded else "\u25b8"
        Animation(color=Theme.accent_light if expanded else Theme.fg_faint,
                  duration=0.15, t="out_cubic").start(self.chev)


class FileTree(ScrollView):
    def __init__(self, root, app, **kw):
        kw.setdefault("bar_width", 4)
        super().__init__(**kw)
        self.app = app
        self.root = root
        self.expanded = set()
        self.active_path = None
        self.rows = []
        self._entries = []
        self._list = BoxLayout(orientation="vertical", size_hint=(1, None),
                               spacing=0)
        self._list.bind(minimum_height=self._list.setter("height"))
        self.add_widget(self._list)
        if root:
            self.refresh()

    def refresh(self):
        self._list.clear_widgets()
        self.rows = []
        self._entries = []
        if self.root and os.path.isdir(self.root):
            self._walk(self.root, 0)
        self._rebuild()

    def _walk(self, directory, depth):
        try:
            items = list(os.scandir(directory))
        except OSError:
            return
        items.sort(key=lambda e: (not e.is_dir(), e.name.lower()))
        for e in items:
            entry = {
                "path": e.path, "name": e.name, "is_dir": e.is_dir(),
                "depth": depth, "dir_path": directory,
            }
            self._entries.append(entry)
            if e.is_dir() and e.path in self.expanded:
                self._walk(e.path, depth + 1)

    def _rebuild(self):
        self._list.clear_widgets()
        self.rows = []
        for entry in self._entries:
            row = FileRow(self, entry["path"], entry["name"], entry["is_dir"],
                          entry["depth"])
            row.opacity = 0
            row._indent.width = entry["depth"] * 14
            if entry["is_dir"] and entry["path"] in self.expanded:
                row.set_expanded(True)
            self.rows.append(row)
            self._list.add_widget(row)
            Animation(opacity=1, duration=0.16, t="out_cubic").start(row)

    def on_row_click(self, row):
        if row.is_dir:
            if row.path in self.expanded:
                self.expanded.discard(row.path)
            else:
                self.expanded.add(row.path)
            self.refresh()
        else:
            self.active_path = row.path
            for r in self.rows:
                r._draw()
            if self.app:
                self.app.open_file(row.path)
