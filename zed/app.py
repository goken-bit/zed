import os

from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Keyboard, Window
from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label

from zed import runner
from zed.project import Settings
from zed.theme import Theme, rgba
from zed.widgets.activitybar import ActivityBar
from zed.widgets.base import AnimatedButton, Hoverable, ToastManager
from zed.widgets.editor import CodeEditor
from zed.widgets.editorpane import EditorPane
from zed.widgets.filebrowser import FileBrowser, PromptDialog
from zed.widgets.modal import Modal
from zed.widgets.settingspanel import ZedSettings as SettingsPanel
from zed.widgets.sidebar import Sidebar
from zed.widgets.statusbar import StatusBar
from zed.widgets.tabs import TabBar
from zed.widgets.terminal import Terminal
from zed.widgets.titlebar import TitleBar
from zed.widgets.syntax import language_for

KC = Keyboard.keycodes

VARIANTS = [
    ("Dark+", "#007acc", "#2aa4ff", "#062e4a"),
    ("Midnight", "#7c4dff", "#a07cff", "#1b0f3f"),
    ("Emerald", "#00b894", "#38d9a9", "#002f26"),
    ("Sunset", "#e17055", "#ff9a76", "#3d1508"),
]


class MenuRow(Hoverable):
    def __init__(self, label, fn, menu, **kw):
        super().__init__(**kw)
        self.size_hint = (1, None)
        self.height = 38
        self.normal_color = (0, 0, 0, 0)
        self.hover_color = (1, 1, 1, 0.06)
        self.background_normal = ""
        self.background_down = ""
        self.border = (0, 0, 0, 0)
        self.fn = fn
        self.menu = menu
        box = BoxLayout(size_hint=(1, 1), padding=(16, 0, 16, 0))
        lbl = Label(text=label, font_name=Theme.font_ui, font_size=13,
                    color=Theme.fg, halign="left", valign="middle")
        box.add_widget(lbl)
        self.add_widget(box)

    def on_release(self):
        self.menu.close()
        Clock.schedule_once(lambda dt: self.fn(), 0.03)


class MenuModal(Modal):
    def __init__(self, app, items, **kw):
        super().__init__(**kw)
        self.app = app
        self.panel = BoxLayout(orientation="vertical", size_hint=(None, None),
                               width=230, spacing=0)
        with self.panel.canvas.before:
            Color(*Theme.bg_panel)
            self._bg = Rectangle()
            Color(1, 1, 1, 0.12)
            self._border = Rectangle(size=(2, 2))
        self.panel.bind(pos=self._draw, size=self._draw)
        for label, fn in items:
            self.panel.add_widget(MenuRow(label, fn, self))
        self.add_widget(self.panel)
        self._draw()

    def _draw(self, *a):
        self._bg.pos = self.panel.pos
        self._bg.size = self.panel.size
        self._border.pos = self.panel.pos
        self._border.size = self.panel.size

    def _panel_y(self):
        return self.height - self.panel.height - 46

    def open(self):
        self.panel.height = len(self.panel.children) * 38
        super().open()


class Splash(FloatLayout):
    def __init__(self, **kw):
        super().__init__(**kw)
        with self.canvas.before:
            Color(*Theme.bg_deep)
            self._bg = Rectangle()
        self.bind(size=self._draw)
        self._draw()
        self._center = BoxLayout(size_hint=(None, None), spacing=4, padding=(0, 0, 0, 60))
        self._labels = []
        for ch in "Zed":
            lbl = Label(text=ch, font_name=Theme.font_ui, font_size=46,
                        color=Theme.fg, bold=True, size=(52, 64))
            lbl.opacity = 0
            self._center.add_widget(lbl)
            self._labels.append(lbl)
        self._sub = Label(text="a lightweight IDE", font_name=Theme.font_ui,
                          font_size=14, color=Theme.fg_faint, size=(220, 24))
        self.add_widget(self._center)
        self.add_widget(self._sub)
        self.bind(size=self._place)
        self._place()

    def _draw(self, *a):
        self._bg.pos = self.pos
        self._bg.size = self.size

    def _place(self, *a):
        self._center.pos = (self.width / 2 - 90, self.height / 2 - 20)
        self._sub.pos = (self.width / 2 - 110, self.height / 2 - 70)

    def play(self, on_done):
        for i, lbl in enumerate(self._labels):
            Clock.schedule_once(
                lambda dt, l=lbl: Animation(opacity=1, font_size=40, duration=0.35,
                                            t="out_back").start(l), 0.1 + i * 0.12)
        Clock.schedule_once(lambda dt: Animation(opacity=1, duration=0.3).start(self._sub), 0.5)
        Clock.schedule_once(on_done, 1.3)


class ZedApp(App):
    title = "Zed"

    def __init__(self, **kw):
        super().__init__(**kw)
        self.settings = None
        self.active_editor = None
        self.editors = {}
        self.chain = runner.ChainRunner()
        self.sidebar_visible = True
        self.panel_visible = True
        self.variant_idx = 0
        self._modals = []

    def build(self):
        Window.clearcolor = Theme.bg
        if not os.environ.get("ANDROID_ARGUMENT"):
            try:
                Window.size = (430, 800)
            except Exception:
                pass
        base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            ".zed", "settings.json")
        self.settings = Settings(base)
        self._apply_settings()
        self.workdir = os.environ.get("ANDROID_ARGUMENT") or os.getcwd()

        self.root = FloatLayout()
        self.column = BoxLayout(orientation="vertical", spacing=0, size_hint=(1, 1))
        self.middle = BoxLayout(orientation="horizontal", spacing=0)

        self.titlebar = TitleBar(self)
        self.activitybar = ActivityBar(self)
        self.sidebar = Sidebar(self)
        if not self.sidebar_visible:
            self.sidebar.width = 0
        self.tabbar = TabBar(on_change=self.on_tab_change)
        self.pane = EditorPane()
        self.terminal = Terminal(self)
        self.statusbar = StatusBar(self)

        center = BoxLayout(orientation="vertical", spacing=0)
        center.add_widget(self.tabbar)
        center.add_widget(self.pane)
        center.add_widget(self.terminal)

        self.middle.add_widget(self.activitybar)
        self.middle.add_widget(self.sidebar)
        self.middle.add_widget(center)

        self.column.add_widget(self.titlebar)
        self.column.add_widget(self.middle)
        self.column.add_widget(self.statusbar)

        self.root.add_widget(self.column)

        self.toasts = ToastManager(size_hint=(1, 1))
        self.root.add_widget(self.toasts)

        self.settingspanel = SettingsPanel(self, size_hint=(1, 1))
        self.menu = MenuModal(self, [
            ("New File", self.new_file),
            ("New Folder", self.new_folder),
            ("Open File\u2026", lambda: self.open_browser("file")),
            ("Open Folder\u2026", lambda: self.open_browser("folder")),
            ("Save", self.save),
            ("Run (F5)", self.run_active),
            ("Settings", self.open_settings),
            ("Toggle Theme", self.cycle_theme),
            ("About Zed", self.show_about),
            ("Quit", self.quit),
        ], size_hint=(1, 1))
        self._modals = [self.settingspanel, self.menu]
        self.about = None

        self.root.add_widget(self.settingspanel)
        self.root.add_widget(self.menu)

        self.splash = Splash(size_hint=(1, 1))
        self.root.add_widget(self.splash)

        self._make_welcome()

        Window.bind(on_key_down=self._key_down, on_textinput=self._text_input)
        Clock.schedule_once(lambda dt: self.splash.play(self._splash_done), 0.3)
        return self.root

    def _apply_settings(self):
        Theme.anim_enabled = bool(self.settings.get("anim_enabled", True))
        Theme.typing_style = self.settings.get("typing_style", "fade")
        Theme.font_size = int(self.settings.get("font_size", 15))
        Theme.line_height = int(Theme.font_size * 1.6)
        Theme.tab_width = int(self.settings.get("tab_width", 4))
        self.sidebar_visible = bool(self.settings.get("sidebar", True))

    def settings_save(self, key, value):
        if self.settings:
            self.settings.set(key, value)

    def _make_welcome(self):
        editor = CodeEditor()
        self.welcome = editor
        self.pane.set_editor(editor)
        self.active_editor = editor
        self.titlebar.set_file("Welcome to Zed")
        self.statusbar.set_lang("Plain Text")
        self.statusbar.set_cursor(1, 1)
        self.statusbar.set_message("Create a new file or open a folder")

    def _splash_done(self, *a):
        anim = Animation(opacity=0, duration=0.4, t="in_cubic")
        anim.bind(on_complete=lambda *_: self.root.remove_widget(self.splash)
                  if self.splash.parent else None)
        anim.start(self.splash)

    def on_tab_change(self, tab):
        if tab is None:
            self.pane.set_editor(self.welcome)
            self.active_editor = self.welcome
            self.titlebar.set_file("Welcome to Zed")
            self.statusbar.set_lang("Plain Text")
            return
        editor = self.editors.get(tab.filepath)
        if editor is None:
            editor = CodeEditor(tab.filepath)
            editor.on_edit = lambda: self.on_edit(tab.filepath)
            editor.on_cursor = self._cursor_tick
            self.editors[tab.filepath] = editor
        self.pane.set_editor(editor)
        self.active_editor = editor
        self.titlebar.set_file(os.path.basename(tab.filepath), tab.dirty)
        self.statusbar.set_lang(self._lang_name(tab.filepath))
        self.sidebar.mark_active(tab.filepath)
        self._cursor_tick()

    def _lang_name(self, path):
        lexer = language_for(path)
        names = {".py": "Python", ".cpp": "C++", ".cc": "C++", ".cxx": "C++",
                 ".c": "C++", ".h": "C++", ".hpp": "C++"}
        return names.get(os.path.splitext(path)[1].lower(), "Plain Text")

    def _cursor_tick(self, *a):
        if self.active_editor:
            line, col = self.active_editor.cursor
            self.statusbar.set_cursor(line + 1, col + 1)

    def on_edit(self, path):
        tab = self.tabbar.activate_path(path)
        if tab:
            tab.set_dirty(True)
            self.titlebar.set_file(os.path.basename(path), True)
            self.statusbar.set_message("Unsaved changes")

    def open_file(self, path):
        if not path:
            return
        path = os.path.abspath(path)
        tab = self.tabbar.activate_path(path)
        if tab:
            return
        editor = self.editors.get(path)
        if editor is None:
            editor = CodeEditor(path)
            editor.on_edit = lambda: self.on_edit(path)
            editor.on_cursor = self._cursor_tick
            self.editors[path] = editor
        self.tabbar.add_tab(path, os.path.basename(path))
        self.statusbar.set_message("Opened %s" % os.path.basename(path))

    def save(self, *a):
        editor = self.active_editor
        if not editor or not editor.path:
            self.toasts.toast("Nothing to save", "warning")
            return
        if editor.save():
            tab = self.tabbar.activate_path(editor.path)
            if tab:
                tab.set_dirty(False)
            self.titlebar.set_file(os.path.basename(editor.path), False)
            self.statusbar.set_message("Saved")
            self.toasts.toast("Saved", "success")
        else:
            self.toasts.toast("Save failed", "error")

    def new_file(self, *a):
        root = self.sidebar.tree.root or self.workdir
        self._prompt("New File", "e.g. main.py", "Create",
                     lambda name: self._create_file(root, name))

    def new_folder(self, *a):
        root = self.sidebar.tree.root or self.workdir
        self._prompt("New Folder", "folder name", "Create",
                     lambda name: self._create_folder(root, name))

    def _prompt(self, title, hint, action, on_done):
        dlg = PromptDialog(self, title, hint, action, on_done, size_hint=(1, 1))
        self._register_modal(dlg)
        self.root.add_widget(dlg)
        dlg.open()

    def _register_modal(self, modal):
        self._modals.append(modal)
        modal.on_close = lambda m: self._discard(m)

    def _discard(self, modal):
        if modal in self._modals:
            self._modals.remove(modal)
        if modal.parent:
            modal.parent.remove_widget(modal)

    def _create_file(self, root, name):
        path = os.path.join(root, name)
        if not os.path.exists(path):
            template = ""
            ext = os.path.splitext(name)[1].lower()
            if ext == ".py":
                template = 'def main():\n    print("Hello, Zed!")\n\n\nif __name__ == "__main__":\n    main()\n'
            elif ext in (".cpp", ".cc", ".cxx"):
                template = ('#include <iostream>\n\n'
                            'int main() {\n    std::cout << "Hello, Zed!" << std::endl;\n'
                            '    return 0;\n}\n')
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(template)
            except OSError:
                self.toasts.toast("Cannot create file", "error")
                return
        self.sidebar.refresh()
        self.open_file(path)
        self.toasts.toast("Created %s" % name, "success")

    def _create_folder(self, root, name):
        path = os.path.join(root, name)
        try:
            os.makedirs(path, exist_ok=True)
        except OSError:
            self.toasts.toast("Cannot create folder", "error")
            return
        self.sidebar.refresh()
        self.toasts.toast("Created %s" % name, "success")

    def open_browser(self, mode):
        fb = FileBrowser(self, mode=mode,
                         title="Open Folder" if mode == "folder" else "Open File",
                         size_hint=(1, 1))
        self.filebrowser = fb
        self._register_modal(fb)
        self.root.add_widget(fb)
        fb.open()

    def open_folder(self, *a):
        self.open_browser("folder")

    def set_root(self, path):
        self.workdir = path
        self.sidebar.set_root(path)
        self.statusbar.set_message("Folder: %s" % os.path.basename(path))
        self.toasts.toast("Opened %s" % os.path.basename(path), "success")

    def run_active(self, *a):
        editor = self.active_editor
        if not editor or not editor.path:
            self.toasts.toast("Open a file to run it", "warning")
            return
        self.save()
        kind, name = runner.lang_info(editor.path)
        self.terminal.on_run_start(name)
        cwd = os.path.dirname(editor.path) or self.workdir

        def line(t):
            Clock.schedule_once(lambda dt: self.terminal.write(t), 0)

        def done(rc, el):
            Clock.schedule_once(lambda dt: self.terminal.on_run_done(rc, el), 0)

        self.chain = runner.ChainRunner()
        if kind == "python":
            self.chain.start(runner.run_python(editor.path, cwd, line, done))
        elif kind == "cpp":
            self._cpp(editor.path, cwd, line, done)

    def _cpp(self, file, cwd, line, done):
        cache_dir = os.path.join(os.path.expanduser("~"), ".zed", "cache")
        os.makedirs(cache_dir, exist_ok=True)
        out = os.path.join(cache_dir, "zed_run_%d" % os.getpid())
        cmd = runner.cpp_compile_cmd(file, out)
        if cmd is None:
            line("[no C++ compiler found]")
            done(127, 0)
            return
        line("[\u2699 compiling \u2500]")
        r1 = runner.Runner(cmd, cwd, line,
                           lambda rc, el: self._on_compiled(rc, el, out, cwd, line, done))
        self.chain.start(r1)

    def _on_compiled(self, rc, el, out, cwd, line, done):
        if rc != 0:
            done(rc, el)
            return
        line("[\u25b8 running binary \u2500]")
        r2 = runner.Runner([out], cwd, line, done)
        self.chain.start(r2)

    def stop_run(self, *a):
        self.chain.stop()
        self.terminal.write("\n[\u2715 stopped]\n")

    def send_run_input(self, text):
        self.chain.send(text)

    def toggle_sidebar(self, *a):
        self.sidebar_visible = not self.sidebar_visible
        target = 220 if self.sidebar_visible else 0
        Animation(width=target, duration=0.22, t="out_cubic").start(self.sidebar)
        self.settings_save("sidebar", self.sidebar_visible)

    def toggle_panel(self, *a):
        self.panel_visible = not self.panel_visible
        target = Theme.panel_h if self.panel_visible else 0
        Animation(height=target, duration=0.22, t="out_cubic").start(self.terminal)

    def open_settings(self, *a):
        self.settingspanel.sync()
        self._open_persistent(self.settingspanel)

    def _open_persistent(self, modal):
        for m in self._modals:
            if m is not modal and m.visible:
                m.close()
        modal.open()

    def menu_more(self, *a):
        self._open_persistent(self.menu)

    def toggle_menu(self, *a):
        if self.menu.visible:
            self.menu.close()
        else:
            self.menu.open()

    def cycle_theme(self, *a):
        self.variant_idx = (self.variant_idx + 1) % len(VARIANTS)
        name, accent, light, deep = VARIANTS[self.variant_idx]
        Theme.accent = rgba(accent)
        Theme.accent_light = rgba(light)
        Theme.accent_bg = rgba(deep)
        self.refresh_accent()
        self.toasts.toast("Theme: %s" % name, "info")
        self.settings_save("variant", name)

    def refresh_accent(self):
        for b in (self.activitybar.explorer, self.activitybar.run,
                  self.activitybar.settings, self.activitybar.theme,
                  self.activitybar.about):
            b._paint()
        self.settingspanel._sync_style()
        if self.statusbar:
            self.statusbar._paint()
        self.titlebar.dot.color = Theme.accent_light

    def show_about(self, *a):
        about = Modal(size_hint=(1, 1))
        panel = BoxLayout(orientation="vertical", size_hint=(None, None),
                          size=(340, 250), padding=(20, 16))
        with panel.canvas.before:
            Color(*Theme.bg_panel)
            self._abg = Rectangle()
        panel.bind(pos=lambda *_: setattr(self._abg, "pos", panel.pos),
                   size=lambda *_: setattr(self._abg, "size", panel.size))
        panel.add_widget(Label(text="Zed", font_name=Theme.font_ui, font_size=34,
                               color=Theme.fg, bold=True))
        panel.add_widget(Label(text="A lightweight, aesthetic IDE for Python & C++",
                               font_name=Theme.font_ui, font_size=13, color=Theme.fg_dim))
        panel.add_widget(Label(text="Built with Kivy 2.3 \u00b7 Pygments \u00b7 clang++",
                               font_name=Theme.font_ui, font_size=12, color=Theme.fg_faint))
        panel.add_widget(Label(text="Press F5 to run \u00b7 Ctrl+S to save",
                               font_name=Theme.font_ui, font_size=12, color=Theme.fg_faint))
        panel.add_widget(BoxLayout())
        btn = AnimatedButton(text="Close", size=(100, 34), font_size=13, on_press=about.close)
        panel.add_widget(btn)
        about.panel = panel
        about.add_widget(panel)
        self.about = about
        self._register_modal(about)
        self.root.add_widget(about)
        about.open()

    def _keyboard_busy(self):
        for m in self._modals:
            if m.visible:
                return True
        if self.terminal.input.focus:
            return True
        return False

    def _key_down(self, window, key, scancode, codepoint, modifiers):
        if key == KC["escape"]:
            if self._keyboard_busy():
                for m in list(self._modals):
                    if m.visible:
                        m.close()
                return True
        if self._keyboard_busy():
            return False
        if "ctrl" not in modifiers and key == KC["f5"]:
            self.run_active()
            return True
        if "ctrl" in modifiers:
            if key == KC["enter"]:
                self.run_active()
                return True
            if key == KC["n"]:
                self.new_file()
                return True
            if key == KC["o"]:
                self.open_browser("file")
                return True
            if key == KC["s"]:
                self.save()
                return True
            if key == KC[","]:
                self.open_settings()
                return True
            if key == KC["b"]:
                self.toggle_sidebar()
                return True
        if not self.active_editor:
            return False
        if "ctrl" in modifiers:
            return self.active_editor.on_ctrl_key(key, scancode, codepoint, modifiers)
        return self.active_editor.on_key(key, scancode, codepoint, modifiers)

    def _text_input(self, window, text):
        if self._keyboard_busy():
            return False
        if self.active_editor:
            self.active_editor.on_text_input(text)
        return True

    def rebuild_fonts(self):
        for editor in self.editors.values():
            editor._refresh_after()
        if self.welcome and self.welcome is not self.active_editor:
            self.welcome._refresh_after()
        self.pane._layout()

    def quit(self, *a):
        if self.chain:
            self.chain.stop()
        self.stop()
