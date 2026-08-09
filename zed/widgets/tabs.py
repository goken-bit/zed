from kivy.animation import Animation
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.properties import ObjectProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView

from zed.theme import Theme
from zed.widgets.base import IconButton


class Tab(BoxLayout):
    def __init__(self, tabbar, filepath, name, **kw):
        super().__init__(**kw)
        self.tabbar = tabbar
        self.filepath = filepath
        self.name = name
        self.dirty = False
        self.size_hint = (None, None)
        self.size = (max(90, len(name) * 8 + 54), 36)
        self.padding = (8, 0, 4, 0)
        self.spacing = 4

        self.label = Label(text=name, font_name=Theme.font_ui, font_size=13,
                           color=Theme.fg_dim, size_hint=(None, 1), width=self.width - 40,
                           halign="left", valign="middle", shorten=True,
                           max_lines=1, text_size=(None, None))
        self.bind(size=lambda *_: setattr(self.label, "text_size", (self.label.width, None)))
        self.dot = Label(text="", font_name=Theme.font_ui, font_size=12,
                         color=Theme.warning, size_hint=(None, 1), width=8)
        self.close = IconButton(text="\u00d7", font_size=14, on_press=self._close,
                                size=(20, 20))
        self.add_widget(self.label)
        self.add_widget(self.dot)
        self.add_widget(self.close)

        self.bind(pos=self._draw, size=self._draw)
        with self.canvas.before:
            self._bg_color = Color(*Theme.bg_alt)
            self._bg = Rectangle()
            Color(*Theme.accent)
            self._accent = Rectangle(size=(0, 2))
        self._draw()

    def _close(self):
        self.tabbar.close_tab(self)

    def _draw(self, *a):
        self._bg.pos = self.pos
        self._bg.size = self.size
        self._accent.pos = (self.x, self.y)
        self._accent.size = (self.width, 2 if self.tabbar.active is self else 0)
        if self.tabbar.active is self:
            self.label.color = Theme.fg
            self._bg_color.rgba = Theme.bg
        else:
            self.label.color = Theme.fg_dim
            self._bg_color.rgba = Theme.bg_alt

    def set_dirty(self, dirty):
        self.dirty = dirty
        self.dot.text = "\u2022" if dirty else ""

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)
        if super().on_touch_down(touch):
            return True
        self.tabbar.activate(self)
        return True


class TabBar(ScrollView):
    active = ObjectProperty(None)

    def __init__(self, on_change=None, **kw):
        kw.setdefault("do_scroll_x", True)
        kw.setdefault("do_scroll_y", False)
        kw.setdefault("bar_width", 4)
        super().__init__(**kw)
        self.on_change = on_change
        self.tabs = []
        self._container = BoxLayout(size_hint=(None, 1), height=36, spacing=0,
                                    padding=0)
        self.add_widget(self._container)

    def add_tab(self, filepath, name):
        tab = Tab(self, filepath, name)
        self.tabs.append(tab)
        self._container.add_widget(tab)
        tab.opacity = 0
        Animation(opacity=1, duration=0.18, t="out_cubic").start(tab)
        self.activate(tab)
        self._reflow()
        Clock.schedule_once(lambda dt: self.scroll_to(tab, padding=0), 0.05)
        return tab

    def close_tab(self, tab):
        anim = Animation(opacity=0, size_hint_x=0, duration=0.15, t="in_cubic")
        anim.bind(on_complete=lambda *_: self._remove_tab(tab))
        anim.start(tab)

    def _remove_tab(self, tab):
        if tab not in self.tabs:
            return
        idx = self.tabs.index(tab)
        self.tabs.remove(tab)
        self._container.remove_widget(tab)
        self._reflow()
        if self.active is tab:
            if self.tabs:
                self.activate(self.tabs[max(0, idx - 1)])
            else:
                self.activate(None)

    def activate(self, tab):
        self.active = tab
        for t in self.tabs:
            t._draw()
        if self.on_change:
            self.on_change(tab)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            return super().on_touch_down(touch)
        return False

    def _reflow(self):
        w = sum(t.width for t in self.tabs)
        self._container.width = max(w, self.width)

    def activate_path(self, path):
        for t in self.tabs:
            if t.filepath == path:
                self.activate(t)
                return t
        return None
