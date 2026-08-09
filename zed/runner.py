import os
import shutil
import subprocess
import sys
import threading
import time


def lang_info(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".py", ".pyw"):
        return "python", "Python"
    if ext in (".cpp", ".cxx", ".cc", ".c", ".h", ".hpp", ".hxx", ".hh", ".ino"):
        return "cpp", "C++"
    return "plain", "Plain Text"


def _cxx():
    for c in ("clang++", "g++", "c++"):
        p = shutil.which(c)
        if p:
            return p
    return None


def python_cmd(file):
    exe = sys.executable or "python3"
    return [exe, "-u", file]


def cpp_compile_cmd(file, out):
    compiler = _cxx()
    if compiler is None:
        return None
    return [compiler, "-std=c++17", "-O1", "-w", "-o", out, file]


class Runner:
    def __init__(self, cmd, cwd, on_line, on_done):
        self.cmd = cmd
        self.cwd = cwd
        self.on_line = on_line
        self.on_done = on_done
        self.proc = None
        self.t0 = time.time()
        self._thread = None
        self._stopped = False

    def start(self):
        if self._thread is not None:
            return self
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def _run(self):
        try:
            self.proc = subprocess.Popen(
                self.cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE, cwd=self.cwd, text=True, bufsize=1,
                errors="replace",
            )
        except Exception as exc:
            self.on_done(127, time.time() - self.t0)
            self.on_line("[cannot start: %s]" % exc)
            return
        try:
            for line in iter(self.proc.stdout.readline, ""):
                self.on_line(line.rstrip("\n"))
        except Exception:
            pass
        rc = self.proc.wait()
        elapsed = time.time() - self.t0
        if self._stopped:
            self.on_done(rc if rc is not None else 0, elapsed)
        else:
            self.on_done(rc, elapsed)

    def send(self, text):
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.stdin.write(text + "\n")
                self.proc.stdin.flush()
            except Exception:
                pass

    def stop(self):
        self._stopped = True
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.terminate()
            except Exception:
                pass
            try:
                self.proc.kill()
            except Exception:
                pass


class ChainRunner:
    def __init__(self):
        self.current = None

    def start(self, runner):
        self.current = runner
        runner.start()
        return runner

    def send(self, text):
        if self.current:
            self.current.send(text)

    def stop(self):
        if self.current:
            self.current.stop()


def run_python(file, cwd, on_line, on_done):
    return Runner(python_cmd(file), cwd, on_line, on_done).start()


def run_cpp(file, cwd, on_line, on_done):
    cache_dir = os.path.join(os.path.expanduser("~"), ".zed", "cache")
    os.makedirs(cache_dir, exist_ok=True)
    out = os.path.join(cache_dir, "zed_run_%d" % os.getpid())
    compile_cmd = cpp_compile_cmd(file, out)
    if compile_cmd is None:
        on_line("[no C++ compiler found]")
        on_done(127, 0)
        return None

    def after_compile(rc, elapsed):
        if rc != 0:
            on_done(rc, elapsed)
            return
        on_line("[\u25b8 running binary \u2500]")
        Runner([out], cwd, on_line, on_done).start()

    Runner(compile_cmd, cwd, on_line, after_compile).start()
    return None
