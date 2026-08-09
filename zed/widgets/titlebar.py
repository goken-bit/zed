from kivy.animation import Animation
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label

from zed.theme import Theme
from zed.widgets.base import IconButton


class TitleBar(BoxLayout):
    def __init__(self, app, **kw):
        super().__init__(**kw)
        self.app = app
        self.size_hint = (1, None)
        self.height = Theme.titlebar_h
        self.padding = (10, 0, 6, 0)
        self.spacing = 6
        with self.canvas.before:
            Color(*Theme.bg_deep)
            self._bg = Rectangle()
            Color(1, 1, 1, 0.06)
            self._line = Rectangle(size=(0, 1))
        self.bind(pos=self._draw, size=self._draw)

        self.logo = []
        logo_box = BoxLayout(size_hint=(None, 1), width=120, spacing=0)
        self.dot = Label(text="\u25cf", font_name=Theme.font_ui, font_size=13,
                         color=Theme.accent_light, size_hint=(None, 1), width=14,
                         valign="middle", halign="center")
        for ch in "Zed":
            lbl = Label(text=ch, font_name=Theme.font_ui, font_size=16,
                        color=Theme.fg, size_hint=(None, 1), width=17,
                        bold=True, valign="middle", halign="center")
            lbl.opacity = 0
            logo_box.add_widget(lbl)
            self.logo.append(lbl)
        logo_box.add_widget(self.dot)
        self.dot.opacity = 0
        self.add_widget(logo_box)

        self.file_lbl = Label(text="Welcome to Zed", font_name=Theme.font_ui,
                              font_size=12, color=Theme.fg_dim, size_hint=(1, 1),
                              halign="center", valign="middle", shorten=True,
                              max_lines=1)
        self.file_lbl.bind(size=lambda *a: setattr(self.file_lbl, "text_size",
                                                   (self.file_lbl.width, None)))
        self.add_widget(self.file_lbl)

        self.menu_btn = IconButton(text="\u2261", font_size=15, size=(30, 30),
                                   on_press=lambda: app.toggle_menu())
        self.min_btn = IconButton(text="\u2501", font_size=13, size=(26, 26),
                                  on_press=self._minimize)
        self.max_btn = IconButton(text="\u25a1", font_size=12, size=(26, 26),
                                  on_press=self._maximize)
        self.close_btn = IconButton(text="\u2715", font_size=12, size=(26, 26),
                                    on_press=app.quit)
        self.add_widget(self.menu_btn)
        self.add_widget(self.min_btn)
        self.add_widget(self.max_btn)
        self.add_widget(self.close_btn)
        Clock.schedule_once(lambda dt: self.play_logo(), 0.15)

    def _draw(self, *a):
        self._bg.pos = self.pos
        self._bg.size = self.size
        self._line.pos = (self.x, self.y)
        self._line.size = (self.width, 1)

    def play_logo(self):
        for i, lbl in enumerate(self.logo):
            lbl.opacity = 0
            lbl.font_size = 26
            Clock.schedule_once(
                lambda dt, l=lbl: Animation(opacity=1, font_size=16, duration=0.3,
                                            t="out_back").start(l),
                0.05 + i * 0.09)
        Animation(opacity=1, duration=0.4, t="out_cubic").start(self.dot)

    def _minimize(self):
        try:
            Window.minimize()
        except Exception:
            pass

    def _maximize(self):
        try:
            Window.fullscreen = not Window.fullscreen
        except Exception:
            pass

    def set_file(self, name, dirty=False):
        suffix = " \u2022" if dirty else ""
        self.file_lbl.text = (name or "Welcome to Zed") + suffix
