from kivy.animation import Animation
from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout

from zed.theme import Theme
from zed.widgets.base import IconButton


class ActivityButton(IconButton):
    def __init__(self, glyph, on_press=None, active=False, **kw):
        kw.setdefault("size", (46, 44))
        kw.setdefault("font_size", 16)
        super().__init__(text=glyph, on_press=on_press, **kw)
        self.active = active
        with self.canvas.after:
            self._bar_color = Color(*Theme.accent)
            self._bar = Rectangle(size=(3, 0))
        self.bind(pos=self._draw, size=self._draw)
        self.bind(hovered=self._paint)
        self._paint()

    def _draw(self, *a):
        self._bar.pos = (self.x, self.y)

    def _paint(self, *a):
        target_h = self.height if self.active else 0
        target_color = Theme.accent if self.active else Theme.accent_bg
        Animation(size=(3, target_h), duration=0.22, t="out_cubic").start(self._bar)
        Animation(rgba=target_color, duration=0.22).start(self._bar_color)
        self.color = Theme.fg if self.active else (0.6, 0.6, 0.63, 1)


class ActivityBar(BoxLayout):
    def __init__(self, app, **kw):
        super().__init__(**kw)
        self.app = app
        self.size_hint = (None, 1.0)
        self.width = Theme.activitybar_w
        self.orientation = "vertical"
        self.spacing = 0
        self.padding = (0, 6, 0, 6)
        with self.canvas.before:
            Color(*Theme.bg_deep)
            self._bg = Rectangle()
        self.bind(pos=self._draw, size=self._draw)

        self.explorer = ActivityButton("\u25a6", on_press=self._explorer, active=True)
        self.run = ActivityButton("\u25b6", on_press=self._run)
        self.settings = ActivityButton("\u2699", on_press=self._settings)
        self.theme = ActivityButton("\u25d0", on_press=self._theme)
        self.about = ActivityButton("\u24d8", on_press=self._about)

        self.add_widget(self.explorer)
        self.add_widget(self.run)
        self.add_widget(BoxLayout())
        self.add_widget(self.settings)
        self.add_widget(self.theme)
        self.add_widget(self.about)

    def _draw(self, *a):
        self._bg.pos = self.pos
        self._bg.size = self.size

    def set_active(self, btn):
        for b in (self.explorer, self.run, self.settings, self.theme, self.about):
            b.active = b is btn
            b._paint()

    def _explorer(self):
        self.set_active(self.explorer)
        self.app.toggle_sidebar()

    def _run(self):
        self.set_active(self.run)
        self.app.toggle_panel()

    def _settings(self):
        self.set_active(self.settings)
        self.app.open_settings()

    def _theme(self):
        self.set_active(self.theme)
        self.app.cycle_theme()

    def _about(self):
        self.set_active(self.about)
        self.app.show_about()
