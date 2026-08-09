import os
import sys


def main():
    os.environ.setdefault("KIVY_NO_ARGS", "1")
    from zed.app import ZedApp
    ZedApp().run()


if __name__ == "__main__":
    main()
