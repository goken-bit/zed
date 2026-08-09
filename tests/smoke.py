import os
import sys
import tempfile

os.environ["KIVY_WINDOW"] = "mock"
os.environ["KIVY_NO_ARGS"] = "1"
os.environ["KIVY_LOG_MODE"] = "MIXED"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FAILURES = []
REPORT = []


def report(text):
    REPORT.append(text)
    print(text)


def check(name, cond, detail=""):
    if cond:
        report("PASS: %s" % name)
    else:
        FAILURES.append(name)
        report("FAIL: %s %s" % (name, detail))


def test_highlight():
    from zed.widgets.syntax import Highlighter, language_for
    from pygments.lexers import PythonLexer, CppLexer

    h = Highlighter(PythonLexer)
    lines = h.lines_for('def foo():\n    x = "hi"\n    return 1  # ok\n', 1)
    check("py highlighter tokens", len(lines) == 4 and lines[0].startswith("[color=#"), repr(lines))
    check("py string color", "#CE9178" in lines[1])
    check("py comment color", "#6A9955" in lines[2])

    h2 = Highlighter(CppLexer)
    cpp = h2.lines_for('#include <iostream>\nint main() { return 0; }\n', 1)
    check("cpp highlighter tokens", len(cpp) == 3 and "[color=" in cpp[0], repr(cpp))

    check("lang detect py", language_for("a.py") is PythonLexer)
    check("lang detect cpp", language_for("b.cpp") is CppLexer)
    check("lang detect none", language_for("c.txt") is None)


def test_editor_ops():
    from kivy.core.window import Window
    if Window is None:
        report("SKIP: editor_ops (no window provider in this env)")
        return
    from zed.widgets.editor import CodeEditor

    ed = CodeEditor()
    ed.set_text("hello\nworld\n")
    ed.cursor = (0, 5)
    ed.type_text("!")
    check("insert", ed.text == "hello!\nworld\n", repr(ed.text))
    ed.type_text("!")
    check("insert 2", ed.text == "hello!!\nworld\n", repr(ed.text))
    check("cursor", ed.cursor == (0, 7))

    ed.cursor = (0, 7)
    ed.delete_back()
    check("backspace", ed.text == "hello!\nworld\n", repr(ed.text))

    ed.undo()
    check("undo", ed.text == "hello!!\nworld\n", repr(ed.text))
    ed.undo()
    check("undo 2", ed.text == "hello!\nworld\n", repr(ed.text))

    ed.set_text("a\nb\nc\n")
    ed.select_all()
    check("select all", ed.selected_text() == "a\nb\nc\n", repr(ed.selected_text()))
    ed.type_text("X")
    check("replace selection", ed.text == "X\n", repr(ed.text))

    ed2 = CodeEditor()
    ed2.set_text("  def f():\n    x\n")
    ed2.cursor = (0, 11)
    ed2.type_newline()
    check("auto indent python", ed2.lines()[1] == "        ", repr(ed2.lines()[1]))

    check("cursor pos", ed2.cursor == (1, 8))


def test_runner():
    from zed.runner import lang_info, run_python

    kind, name = lang_info("x.py")
    check("lang_info python", kind == "python" and name == "Python")
    kind, name = lang_info("x.cpp")
    check("lang_info cpp", kind == "cpp" and name == "C++")

    tmp = tempfile.mkdtemp()
    script = os.path.join(tmp, "t.py")
    with open(script, "w") as f:
        f.write("import os, sys\nos.write(1, b'HELLO_FROM_RUNNER\\n')\n")

    got = []
    import threading
    done = threading.Event()
    result = {}

    def on_line(t):
        got.append(t)

    def on_done(rc, el):
        result["rc"] = rc
        done.set()

    r = run_python(script, tmp, on_line, on_done)
    done.wait(20)
    check("runner exit 0", result.get("rc") == 0)
    check("runner output", any("HELLO_FROM_RUNNER" in l for l in got), repr(got))
    if r and r.proc:
        r.stop()


def test_settings():
    from zed.project import Settings

    d = tempfile.mkdtemp()
    s = Settings(os.path.join(d, "settings.json"))
    s.set("anim_enabled", False)
    check("settings persisted", Settings(os.path.join(d, "settings.json")).get("anim_enabled") is False)
    check("settings default", s.get("font_size") == 15)


def test_app_build():
    from kivy.core.window import Window
    if Window is None:
        report("SKIP: app_build (no window provider in this env)")
        return
    from kivy.clock import Clock
    tmp = tempfile.mkdtemp()
    hello = os.path.join(tmp, "hello.py")
    with open(hello, "w") as f:
        f.write("import os\nos.write(1, b'APP_RAN_OK\\n')\n")
    from zed.app import ZedApp
    app = ZedApp()
    app.workdir = tmp
    root = app.build()
    check("app builds root", root is not None)
    check("app pane ready", app.pane.editor is not None)
    app.open_file(hello)
    check("app opens file", app.active_editor is not None and app.active_editor.path == hello)
    app.active_editor.type_text("x")
    check("app edit", app.active_editor.text.strip().endswith("x"))
    app.save()
    with open(hello) as f:
        content = f.read()
    check("app saves", "x" in content)
    app.open_settings()
    app.cycle_theme()
    app.toggle_sidebar()
    app.toggle_panel()
    check("app panels toggle", True)

    app.run_active()
    Clock.schedule_once(lambda dt: app.stop(), 4)
    app.run()
    texts = []
    for child in app.terminal.lines_box.children:
        texts.append(child.text)
    joined = "".join(texts)
    check("app runs python", "APP_RAN_OK" in joined, joined[:160])
    check("app exit ok", "exited 0" in joined, joined[:160])


def test_theme():
    from zed.theme import Theme

    check("theme colors", len(Theme.accent) == 4)
    check("fonts exist", os.path.exists(Theme.font_mono))


def main():
    out_file = os.environ.get("ZED_SMOKE_OUT", os.path.join(tempfile.gettempdir(), "zed_smoke.txt"))
    try:
        test_highlight()
        test_editor_ops()
        test_runner()
        test_settings()
        test_theme()
        test_app_build()
    finally:
        with open(out_file, "w") as f:
            f.write("\n".join(REPORT))
            f.write("\nRESULT: %s\n" % ("FAILED" if FAILURES else "OK"))
    if FAILURES:
        sys.exit(1)
    os._exit(0)


if __name__ == "__main__":
    main()
