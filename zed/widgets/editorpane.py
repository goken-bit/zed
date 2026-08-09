from kivy.uix.widget import Widget

from zed.theme import Theme
from zed.widgets.editor import Gutter


class EditorPane(Widget):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.editor = None
        self.gutter = Gutter()
        self.add_widget(self.gutter)
        self.bind(pos=self._layout, size=self._layout)

    def set_editor(self, editor):
        if self.editor is editor:
            return
        if self.editor is not None and self.editor.parent is self:
            self.remove_widget(self.editor)
        self.editor = editor
        editor._gutter = self.gutter
        self.add_widget(editor)
        self._layout()

    def _layout(self, *a):
        if self.editor is None:
            return
        gw = 3 * Theme.font_size + Theme.gutter_pad
        self.gutter.width = gw
        self.gutter.pos = (self.x, self.y)
        self.gutter.size = (gw, self.height)
        self.editor.pos = (self.x + gw, self.y)
        self.editor.size = (max(1, self.width - gw), self.height)
        self.gutter.update(self.editor)
