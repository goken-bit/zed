import os
import sys
import traceback


def _log_paths():
    paths = []
    env_ap = os.environ.get("ANDROID_ARGUMENT")
    if env_ap:
        paths.append(os.path.join(env_ap, "zed_stage.log"))
    for base in ("/storage/emulated/0/Android/data/org.zed.zed/files",
                 "/sdcard/Download", os.getcwd()):
        try:
            p = os.path.join(base, "zed_stage.log")
            paths.append(p)
        except Exception:
            pass
    return paths


def _log_stage(msg):
    text = msg + "\n"
    print(text, end="", flush=True)
    try:
        sys.stderr.write(text)
        sys.stderr.flush()
    except Exception:
        pass
    for p in _log_paths():
        try:
            with open(p, "a") as f:
                f.write(text)
        except Exception:
            pass


def _write_crash(tb):
    try:
        for p in _log_paths():
            crash = p.replace("zed_stage.log", "zed_crash.log")
            with open(crash, "a") as f:
                f.write(tb)
    except Exception:
        pass


def main():
    os.environ.setdefault("KIVY_NO_ARGS", "1")
    _log_stage("start")
    try:
        try:
            import faulthandler
            faulthandler.enable()
        except Exception:
            pass
        _log_stage("importing kivy")
        from kivy.app import App
        from kivy.core.window import Window
        _log_stage("kivy imported")
        from zed.app import ZedApp
        _log_stage("zed imported")
        app = ZedApp()
        _log_stage("app created")
        app.run()
        _log_stage("app stopped")
    except Exception:
        tb = traceback.format_exc()
        _write_crash(tb)
        _log_stage("CRASH: " + tb)
        raise
    except SystemExit:
        _log_stage("app exited")


main()
