import os

from kivy.animation import Animation
from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label

from zed.theme import Theme
from zed.widgets.base import IconButton
from zed.widgets.filetree import FileTree


class Sidebar(BoxLayout):
    def __init__(self, app, **kw):
        kw.setdefault("orientation", "vertical")
        kw.setdefault("spacing", 0)
        super().__init__(**kw)
        self.app = app
        self.size_hint = (None, 1.0)
        self.width = Theme.sidebar_w
        with self.canvas.before:
            Color(*Theme.bg_alt)
            self._bg = Rectangle()
        self.bind(pos=self._draw, size=self._draw)

        header = BoxLayout(size_hint=(1, None), height=38, padding=(10, 0, 6, 0),
                           spacing=2)
        self.title = Label(text="EXPLORER", font_name=Theme.font_ui, font_size=11,
                           color=Theme.fg_faint, size_hint=(1, 1), halign="left",
                           valign="middle")
        header.add_widget(self.title)
        header.add_widget(IconButton(text="\uff0b", font_size=14, size=(26, 26),
                                     on_press=lambda: app.new_file()))
        header.add_widget(IconButton(text="\u21bb", font_size=14, size=(26, 26),
                                     on_press=self.refresh))
        header.add_widget(IconButton(text="\u22ee", font_size=16, size=(26, 26),
                                     on_press=lambda: app.menu_more()))

        self.tree = FileTree(root=self._default_root(), app=app)
        self.tree.on_file = None

        footer = BoxLayout(size_hint=(1, None), height=34, padding=(8, 0, 8, 0),
                           spacing=4)
        self.root_label = Label(text=self._root_name(), font_name=Theme.font_ui,
                                font_size=11, color=Theme.fg_dim, size_hint=(1, 1),
                                halign="left", valign="middle", shorten=True)
        footer.add_widget(self.root_label)
        footer.add_widget(IconButton(text="\u229e", font_size=13, size=(24, 24),
                                     on_press=lambda: app.open_folder()))

        self.add_widget(header)
        self.add_widget(self.tree)
        self.add_widget(footer)

    def _draw(self, *a):
        self._bg.pos = self.pos
        self._bg.size = self.size

    def _default_root(self):
        root = self.app.workdir if getattr(self.app, "workdir", None) else os.getcwd()
        return root

    def _root_name(self):
        root = self.tree.root
        return root if root else "no folder"

    def refresh(self):
        self.tree.refresh()
        self.root_label.text = self._root_name()

    def set_root(self, path):
        self.tree.root = path
        self.tree.expanded.clear()
        self.tree.refresh()
        self.root_label.text = path

    def mark_active(self, path):
        self.tree.active_path = path
        for row in self.tree.rows:
            row._draw()
