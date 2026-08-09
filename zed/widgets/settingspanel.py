from kivy.animation import Animation
from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget

from zed.theme import Theme
from zed.widgets.base import AnimatedButton, IconButton
from zed.widgets.modal import Modal, Toggle


class SegButton(AnimatedButton):
    def __init__(self, text, group, key, **kw):
        kw.setdefault("size", (110, 32))
        kw.setdefault("font_size", 12)
        super().__init__(text=text, **kw)
        self.group = group
        self.key = key
        self.active = False
        self._paint()

    def _paint(self):
        if self.active:
            self.base_color = [*Theme.accent[:3], 1.0]
            self.color = (1, 1, 1, 1)
        else:
            self.base_color = [0.14, 0.14, 0.15, 1.0]
            self.color = (0.75, 0.75, 0.78, 1)
        self.background_color = self.base_color

    def activate(self):
        self.active = True
        Animation(background_color=[*Theme.accent[:3], 1.0], duration=0.2,
                  t="out_cubic").start(self)
        self.color = (1, 1, 1, 1)


class ZedSettings(Modal):
    def __init__(self, app, **kw):
        super().__init__(**kw)
        self.app = app
        self._build_panel()

    def _build_panel(self):
        self.panel = BoxLayout(orientation="vertical", size_hint=(None, None),
                               size=(330, 380), spacing=4)
        with self.panel.canvas.before:
            Color(*Theme.bg_panel)
            self._panel_bg = Rectangle()
            Color(1, 1, 1, 0.1)
            self._panel_border = Rectangle(size=(2, 2))
        self.panel.bind(pos=self._panel_draw, size=self._panel_draw)

        header = BoxLayout(size_hint=(1, None), height=44, padding=(16, 0, 8, 0))
        header.add_widget(Label(text="Settings", font_name=Theme.font_ui,
                                font_size=15, color=Theme.fg, halign="left",
                                valign="middle"))
        header.add_widget(IconButton(text="\u2715", font_size=13, size=(28, 28),
                                     on_press=self.close))
        self.panel.add_widget(header)

        row_anim = BoxLayout(size_hint=(1, None), height=44, padding=(16, 0, 16, 0))
        row_anim.add_widget(self._label("Animations"))
        row_anim.add_widget(BoxLayout())
        self.anim_toggle = Toggle(on_press=self._on_anim)
        self.anim_toggle.set_value(Theme.anim_enabled)
        row_anim.add_widget(self.anim_toggle)
        self.panel.add_widget(row_anim)

        self.panel.add_widget(self._label("Letter animation", small=True))
        seg = BoxLayout(size_hint=(1, None), height=40, padding=(16, 0, 16, 0),
                        spacing=8)
        self.style_buttons = []
        for key, label in (("fade", "Fade + Pop"), ("glow", "Glow Pulse"),
                           ("type", "Typewriter")):
            b = SegButton(label, "style", key, on_press=lambda k=key: self._on_style(k))
            seg.add_widget(b)
            self.style_buttons.append(b)
        self.panel.add_widget(seg)
        self._sync_style()

        row_font = BoxLayout(size_hint=(1, None), height=44, padding=(16, 0, 16, 0))
        row_font.add_widget(self._label("Font size"))
        row_font.add_widget(BoxLayout())
        self.font_val = self._label(str(Theme.font_size))
        row_font.add_widget(AnimatedButton(text="\u2212", size=(34, 30),
                                           on_press=lambda: self._step_font(-1)))
        row_font.add_widget(self.font_val)
        row_font.add_widget(AnimatedButton(text="+", size=(34, 30),
                                           on_press=lambda: self._step_font(1)))
        self.panel.add_widget(row_font)

        row_tab = BoxLayout(size_hint=(1, None), height=44, padding=(16, 0, 16, 0))
        row_tab.add_widget(self._label("Tab width"))
        row_tab.add_widget(BoxLayout())
        self.tab_val = self._label(str(Theme.tab_width))
        row_tab.add_widget(AnimatedButton(text="\u2212", size=(34, 30),
                                          on_press=lambda: self._step_tab(-1)))
        row_tab.add_widget(self.tab_val)
        row_tab.add_widget(AnimatedButton(text="+", size=(34, 30),
                                          on_press=lambda: self._step_tab(1)))
        self.panel.add_widget(row_tab)

        self.panel.add_widget(BoxLayout())
        self.panel.add_widget(self._label("Zed \u00b7 lightweight IDE", small=True))

        self.add_widget(self.panel)
        self._panel_draw()

    def _panel_draw(self, *a):
        self._panel_bg.pos = self.panel.pos
        self._panel_bg.size = self.panel.size
        self._panel_border.pos = self.panel.pos
        self._panel_border.size = self.panel.size

    def _label(self, text, small=False):
        return Label(text=text, font_name=Theme.font_ui,
                     font_size=11 if small else 13, color=Theme.fg_dim,
                     halign="left", valign="middle")

    def sync(self):
        self.anim_toggle.set_value(Theme.anim_enabled)
        self.font_val.text = str(Theme.font_size)
        self.tab_val.text = str(Theme.tab_width)
        self._sync_style()

    def _paint(self):
        self._sync_style()

    def _sync_style(self):
        for b in self.style_buttons:
            on = (Theme.typing_style == b.key)
            b.active = on
            b._paint()
            if on:
                b.activate()

    def _on_anim(self, value):
        Theme.anim_enabled = value
        self.app.settings_save("anim_enabled", value)
        self.app.status.set_anim(value)
        self.app.toasts.toast("Animations %s" % ("on" if value else "off"))

    def _on_style(self, key):
        Theme.typing_style = key
        for b in self.style_buttons:
            if b.key == key:
                b.activate()
            else:
                b.active = False
                b._paint()
        self.app.settings_save("typing_style", key)
        self.app.toasts.toast("Typing style: %s" % key.capitalize())

    def _step_font(self, delta):
        n = max(10, min(30, Theme.font_size + delta))
        if n == Theme.font_size:
            return
        Theme.font_size = n
        Theme.line_height = int(n * 1.6)
        self.font_val.text = str(n)
        self.app.settings_save("font_size", n)
        self.app.rebuild_fonts()

    def _step_tab(self, delta):
        n = max(2, min(8, Theme.tab_width + delta))
        if n == Theme.tab_width:
            return
        Theme.tab_width = n
        self.tab_val.text = str(n)
        self.app.settings_save("tab_width", n)
