from kivy.animation import Animation
from kivy.graphics import Color, Rectangle
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget

from zed.theme import Theme


class Modal(FloatLayout):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.visible = False
        self.on_close = None
        self.bind(size=self._dim)
        with self.canvas.before:
            self._dim_color = Color(0.0, 0.0, 0.0, 0)
            self._dim = Rectangle(size=self.size)

    def _dim(self, *a):
        self._dim.size = self.size

    def open(self):
        self.visible = True
        self.opacity = 1
        Animation(rgba=(0, 0, 0, 0.45), duration=0.22, t="out_cubic").start(self._dim_color)
        if hasattr(self, "panel"):
            self.panel.opacity = 0
            self.panel.y = -self.panel.height - 20
            Animation(opacity=1, y=self._panel_y(), duration=0.26,
                      t="out_back").start(self.panel)

    def _panel_y(self):
        return self.height * 0.05

    def close(self):
        if not self.visible:
            return
        self.visible = False
        anim = Animation(rgba=(0, 0, 0, 0), duration=0.18, t="in_cubic")
        if hasattr(self, "panel"):
            a = Animation(opacity=0, y=self.panel.y - 30, duration=0.18, t="in_cubic")
            a.bind(on_complete=lambda *_: self._gone())
            a.start(self.panel)
        anim.start(self._dim_color)
        self._dim_anim = anim

    def _gone(self):
        self.visible = False
        self.opacity = 0
        if self.on_close:
            self.on_close(self)

    def on_touch_down(self, touch):
        if not self.visible:
            return False
        if hasattr(self, "panel") and self.panel.collide_point(*touch.pos):
            return super().on_touch_down(touch)
        self.close()
        return True


class Toggle(Widget):
    def __init__(self, on_press=None, **kw):
        super().__init__(**kw)
        self.size_hint = (None, None)
        self.size = (44, 24)
        self.value = False
        self.on_press = on_press
        with self.canvas:
            self._track_color = Color(0.3, 0.3, 0.32, 1)
            self._track = Rectangle(size=self.size)
            Color(1, 1, 1, 1)
            self._knob = Rectangle(size=(20, 20))
        self.bind(pos=self._draw, size=self._draw)
        self._draw()

    def _draw(self, *a):
        self._track.pos = self.pos
        self._track.size = self.size
        self._knob.pos = (self.x + (self.size[0] - 22 if self.value else 2),
                          self.y + 2)

    def set_value(self, value):
        self.value = bool(value)
        self._animate()

    def _animate(self):
        target = (self.x + self.size[0] - 22, self.y + 2) if self.value else (self.x + 2, self.y + 2)
        Animation(pos=target, duration=0.2, t="out_cubic").start(self._knob)
        target_color = Theme.accent if self.value else (0.3, 0.3, 0.32, 1)
        Animation(rgba=target_color, duration=0.2, t="out_cubic").start(self._track_color)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.set_value(not self.value)
            if self.on_press:
                self.on_press(self.value)
            return True
        return super().on_touch_down(touch)
