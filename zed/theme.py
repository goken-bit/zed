import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(BASE_DIR, "assets")
FONT_DIR = os.path.join(ASSETS, "fonts")

FONT_MONO = os.path.join(FONT_DIR, "DejaVuSansMono.ttf")
FONT_MONO_BOLD = os.path.join(FONT_DIR, "DejaVuSansMono-Bold.ttf")
FONT_UI = os.path.join(FONT_DIR, "DejaVuSans.ttf")


def _is_font(path):
    try:
        with open(path, "rb") as f:
            head = f.read(4)
        return head in (b"\x00\x01\x00\x00", b"OTTO", b"ttcf")
    except Exception:
        return False


if not (_is_font(FONT_MONO) and _is_font(FONT_MONO_BOLD)
        and _is_font(FONT_UI)):
    FONT_MONO = "RobotoMono"
    FONT_MONO_BOLD = "RobotoMono"
    FONT_UI = "Roboto"


def rgba(hex_color, alpha=1.0):
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)) + (alpha,)


class Theme:
    bg_deep = rgba("#141414")
    bg = rgba("#1e1e1e")
    bg_alt = rgba("#252526")
    bg_panel = rgba("#252526")
    bg_hover = rgba("#2a2d2e")
    bg_active = rgba("#37373d")
    bg_input = rgba("#2b2b2b")
    fg = rgba("#d4d4d4")
    fg_dim = rgba("#9d9d9d")
    fg_faint = rgba("#6e6e6e")
    accent = rgba("#007acc")
    accent_light = rgba("#2aa4ff")
    accent_bg = rgba("#062e4a")
    success = rgba("#4ec9b0")
    warning = rgba("#dcdcaa")
    error = rgba("#f14c4c")
    border = rgba("#3c3c3c")
    caret = rgba("#aeafad")
    selection_bg = rgba("#264f78", 0.5)
    current_line = rgba("#ffffff", 0.05)

    font_mono = FONT_MONO
    font_mono_bold = FONT_MONO_BOLD
    font_ui = FONT_UI

    font_size = 15
    line_height = int(font_size * 1.6)

    titlebar_h = 44
    activitybar_w = 46
    sidebar_w = 220
    statusbar_h = 24
    panel_h = 170
    gutter_pad = 12
    edge = 6

    anim_dur = 0.18
    anim_soft = 0.32
    typing_style = "fade"
    anim_enabled = True
    tab_width = 4

    token_colors = {}

    def apply_tokens(self, mapping):
        self.token_colors.update(mapping)
