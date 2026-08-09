from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label

from zed.theme import Theme


class StatusBar(BoxLayout):
    def __init__(self, app, **kw):
        super().__init__(**kw)
        self.app = app
        self.size_hint = (1, None)
        self.height = Theme.statusbar_h
        self.spacing = 0
        self.padding = (8, 0, 8, 0)
        with self.canvas.before:
            self._bar_color = Color(*Theme.accent)
            self._bar = Rectangle(size=(120, self.height))
            Color(*Theme.bg_deep)
            self._bg = Rectangle()
        self.bind(pos=self._draw, size=self._draw)

        self.lang = self._chip("Python", width=88)
        self.cursor = self._chip("Ln 1, Col 1", width=130)
        self.msg = self._chip("Ready", width=140, grow=True)
        self.spaces = self._chip("Spaces: 4", width=86)
        self.enc = self._chip("UTF-8", width=60)
        self.anim = self._chip("Anim on", width=76)
        self.blank = Label(size_hint=(1, 1))

        self.add_widget(self.lang)
        self.add_widget(self.cursor)
        self.add_widget(self.msg)
        self.add_widget(self.blank)
        self.add_widget(self.spaces)
        self.add_widget(self.enc)
        self.add_widget(self.anim)

    def _chip(self, text, width, grow=False):
        lbl = Label(text=text, font_name=Theme.font_ui, font_size=11,
                    color=Theme.fg_dim, size_hint=(1, 1) if grow else (None, 1),
                    width=width, halign="left", valign="middle")
        return lbl

    def _draw(self, *a):
        self._bar.pos = (self.x, self.y)
        self._bar.size = (min(200, self.width * 0.28), self.height)
        self._bg.pos = (self.x, self.y)
        self._bg.size = self.size

    def _paint(self):
        self._bar_color.rgba = Theme.accent

    def set_lang(self, name):
        self.lang.text = name or "Plain Text"

    def set_cursor(self, line, col):
        self.cursor.text = "Ln %d, Col %d" % (line, col)

    def set_message(self, text):
        self.msg.text = text

    def set_anim(self, on):
        self.anim.text = "Anim %s" % ("on" if on else "off")
