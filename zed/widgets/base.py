from kivy.animation import Animation
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.properties import ListProperty, BooleanProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget

from zed.theme import Theme

_hover_registry = []
_hover_running = False


def _hover_loop(dt):
    try:
        from kivy.core.window import Window
        pos = Window.mouse_pos
    except Exception:
        return
    for h in list(_hover_registry):
        if not h.parent:
            continue
        inside = h.collide_point(*pos)
        if inside and not h.hovered:
            h.hovered = True
            h.on_enter()
        elif not inside and h.hovered:
            h.hovered = False
            h.on_leave()


def _ensure_hover_loop():
    global _hover_running
    if not _hover_running:
        _hover_running = True
        Clock.schedule_interval(_hover_loop, 0.05)


class Hoverable(ButtonBehavior, Widget):
    hovered = BooleanProperty(False)
    hover_color = ListProperty([1.0, 1.0, 1.0, 0.07])
    normal_color = ListProperty([0.0, 0.0, 0.0, 0.0])

    def __init__(self, **kw):
        super().__init__(**kw)
        self.background_normal = ""
        self.background_down = ""
        self.border = (0, 0, 0, 0)
        _hover_registry.append(self)
        _ensure_hover_loop()

    def on_enter(self):
        if not hasattr(self, "background_color"):
            return
        Animation(background_color=self.hover_color, duration=0.15,
                  t="out_cubic").start(self)

    def on_leave(self):
        if not hasattr(self, "background_color"):
            return
        Animation(background_color=self.normal_color, duration=0.22,
                  t="out_cubic").start(self)


class IconButton(Hoverable, Button):
    def __init__(self, text="", on_press=None, **kw):
        kw.setdefault("font_name", Theme.font_ui)
        kw.setdefault("font_size", 16)
        kw.setdefault("background_color", (0, 0, 0, 0))
        kw.setdefault("color", (0.85, 0.85, 0.85, 1))
        kw.setdefault("size_hint", (None, None))
        super().__init__(text=text, **kw)
        self.normal_color = (0, 0, 0, 0)
        self.hover_color = (1, 1, 1, 0.09)
        self.background_color = (0, 0, 0, 0)
        if on_press:
            self.bind(on_press=lambda *_: on_press())


class AnimatedButton(Hoverable, Button):
    def __init__(self, text="", on_press=None, accent=False, **kw):
        kw.setdefault("font_name", Theme.font_ui)
        kw.setdefault("font_size", 13)
        kw.setdefault("background_normal", "")
        kw.setdefault("background_down", "")
        kw.setdefault("size_hint", (None, None))
        super().__init__(text=text, **kw)
        self.border = (0, 0, 0, 0)
        self.accent = accent
        if accent:
            self.base_color = [*Theme.accent[:3], 1.0]
            self.color = (1, 1, 1, 1)
        else:
            self.base_color = [0.16, 0.16, 0.17, 1.0]
            self.color = (0.83, 0.83, 0.83, 1)
        self.normal_color = self.base_color
        self.hover_color = [0.20, 0.20, 0.22, 1.0] if not accent else self.base_color
        self.background_color = self.base_color
        if on_press:
            self.bind(on_press=lambda *_: on_press())

    def on_press(self):
        pressed = [max(0.0, c * 0.8) for c in self.base_color[:3]] + [1.0]
        Animation(background_color=pressed, duration=0.07).start(self)

    def on_release(self):
        Animation(background_color=self.base_color, duration=0.2,
                  t="out_cubic").start(self)


class Toast(Label):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.size_hint = (None, None)
        self.halign = "left"
        self.valign = "middle"
        self.padding = (14, 0)
        self.font_name = Theme.font_ui
        self.font_size = 13
        self.color = (1, 1, 1, 1)
        self.texture_size = (None, None)

    def show(self, message, kind="info"):
        self.text = message
        self.texture_update()
        self.size = (max(90, self.texture_size[0] + 30), 36)
        self.opacity = 0
        with self.canvas.before:
            Color(0.10, 0.10, 0.11, 0.96)
            self._bg = RoundedRectangle(size=self.size, radius=[6])
            Color(*Theme.accent[:3], 1.0)
            self._bar = Rectangle(size=(3, 36))
        self.bind(pos=self._draw, size=self._draw)
        self._draw()
        Animation(opacity=1, duration=0.22, t="out_back").start(self)
        Clock.schedule_once(self._dismiss, 2.4)

    def _draw(self, *a):
        self._bg.pos = self.pos
        self._bar.pos = (self.x, self.y)

    def _dismiss(self, *a):
        anim = Animation(opacity=0, duration=0.28, t="in_cubic")
        anim.bind(on_complete=lambda *_: self.parent.remove_widget(self) if self.parent else None)
        anim.start(self)


class ToastManager(FloatLayout):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.bind(size=self._reflow)

    def _reflow(self, *a):
        y = 12
        for child in self.children:
            child.pos = (self.width - child.width - 14, y)
            y += child.height + 8

    def toast(self, message, kind="info"):
        t = Toast()
        self.add_widget(t)
        t.show(message, kind)
