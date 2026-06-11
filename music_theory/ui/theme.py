"""Application theme: token-driven stylesheets with selectable palettes.

All colors live in named palettes (PALETTES); widgets reference roles via
objectName selectors (QLabel#H1, QPushButton#Choice, ...) so per-widget
setStyleSheet calls stay rare. Font sizes scale with the user's system font
(accessibility: respects "make text bigger" preferences) or an explicit
``ui_scale`` setting, via the factor computed in apply_theme().

Runtime theme switching: apply_theme() rebuilds the QSS *and* updates this
module's color attributes (ACCENT, GOOD, STAFF_PAPER, ...) in place. Custom-
painted widgets and rich-text snippets must therefore read colors through the
module (``from .. import theme`` then ``theme.ACCENT``), never via
``from .theme import ACCENT`` (which freezes the import-time value).

Contrast notes (WCAG AA): text on the accent fill is auto-chosen (black or
white) from the accent's relative luminance; every text/background pair in
each palette meets 4.5:1 on its intended surface. Keyboard focus is always
visible: every interactive widget has a :focus rule, with constant border
widths so focusing never shifts layout.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Palettes
# ---------------------------------------------------------------------------
# Every palette defines the full token set. "dark" is the reference palette;
# the others override the same keys so the QSS template needs no conditionals.

_DARK = {
    "BG": "#15171c",
    "BG_SIDEBAR": "#0f1115",
    "SURFACE": "#1a1d23",        # cards
    "SURFACE_2": "#1d2128",      # inputs, choice buttons
    "SURFACE_3": "#262b34",      # secondary buttons
    "BORDER": "#2c323c",
    "TEXT": "#e7e9ee",
    "TEXT_MUTED": "#9aa3b2",
    "ACCENT": "#5b8def",
    "GOOD": "#3ec46d",
    "GOOD_BG": "#1d3528",
    "BAD": "#e2554e",
    "BAD_BG": "#3a2226",
    "WARN": "#e0a73a",
    "FOCUS": "#e7e9ee",
    "SIDEBAR_TEXT": "#b9bfcc",
    "SIDEBAR_HOVER": "#1c2026",
    "SIDEBAR_TEXT_ACTIVE": "#ffffff",
    "SECONDARY_TEXT": "#d7dbe4",
    "SECONDARY_HOVER": "#2f3540",
    "SECONDARY_PRESSED": "#232831",
    "DANGER_HOVER": "#4a2a2e",
    "CHOICE_CHECKED_BG": "#20283a",
    "DISABLED_BG": "#2a2f38",
    "DISABLED_TEXT": "#6b7280",
    "PROGRESS_BG": "#22262e",
    "STAFF_PAPER": "#f6f3ea",    # warm card the staff is drawn on
    "STAFF_INK": "#1f2228",      # staff lines / clefs / noteheads on the paper
    "TOAST_INFO": "#2f3b52",
    "TOAST_SUCCESS": "#2f7d4f",
    "TOAST_WARNING": "#8a5a1f",
    "TOAST_ERROR": "#8a2f2f",
}

_LIGHT = dict(_DARK, **{
    "BG": "#f2f4f8",
    "BG_SIDEBAR": "#e7eaf1",
    "SURFACE": "#ffffff",
    "SURFACE_2": "#f0f2f6",
    "SURFACE_3": "#e3e7ee",
    "BORDER": "#c6cdd9",
    "TEXT": "#1b1e26",
    "TEXT_MUTED": "#535d6e",
    "ACCENT": "#2f63cf",
    "GOOD": "#177a40",
    "GOOD_BG": "#d9f2e2",
    "BAD": "#b3261e",
    "BAD_BG": "#f9dedc",
    "WARN": "#7a5200",
    "FOCUS": "#1b1e26",
    "SIDEBAR_TEXT": "#3c4454",
    "SIDEBAR_HOVER": "#d9dee8",
    "SIDEBAR_TEXT_ACTIVE": "#10131a",
    "SECONDARY_TEXT": "#272c36",
    "SECONDARY_HOVER": "#d6dbe5",
    "SECONDARY_PRESSED": "#c8cedb",
    "DANGER_HOVER": "#f3cdc9",
    "CHOICE_CHECKED_BG": "#dde7fa",
    "DISABLED_BG": "#dde1e9",
    "DISABLED_TEXT": "#8a93a3",
    "PROGRESS_BG": "#dde1e9",
    "STAFF_PAPER": "#fdfbf4",
    "STAFF_INK": "#1b1e26",
    "TOAST_INFO": "#3b5b9e",
    "TOAST_SUCCESS": "#1f7a47",
    "TOAST_WARNING": "#8a5a1f",
    "TOAST_ERROR": "#a03430",
})

_HIGH_CONTRAST = dict(_DARK, **{
    "BG": "#000000",
    "BG_SIDEBAR": "#000000",
    "SURFACE": "#0a0a0a",
    "SURFACE_2": "#101010",
    "SURFACE_3": "#1c1c1c",
    "BORDER": "#8a8a8a",
    "TEXT": "#ffffff",
    "TEXT_MUTED": "#d2d2d2",
    "ACCENT": "#ffd84d",
    "GOOD": "#5dff95",
    "GOOD_BG": "#003414",
    "BAD": "#ff7a70",
    "BAD_BG": "#420a06",
    "WARN": "#ffc24d",
    "FOCUS": "#ffffff",
    "SIDEBAR_TEXT": "#e8e8e8",
    "SIDEBAR_HOVER": "#1c1c1c",
    "SIDEBAR_TEXT_ACTIVE": "#ffffff",
    "SECONDARY_TEXT": "#ffffff",
    "SECONDARY_HOVER": "#2a2a2a",
    "SECONDARY_PRESSED": "#101010",
    "DANGER_HOVER": "#5c100a",
    "CHOICE_CHECKED_BG": "#2e2a10",
    "DISABLED_BG": "#1c1c1c",
    "DISABLED_TEXT": "#9a9a9a",
    "PROGRESS_BG": "#1c1c1c",
    "STAFF_PAPER": "#ffffff",
    "STAFF_INK": "#000000",
    "TOAST_INFO": "#103a72",
    "TOAST_SUCCESS": "#0c5c2e",
    "TOAST_WARNING": "#7a4d0e",
    "TOAST_ERROR": "#7a1410",
})

_SEPIA = dict(_DARK, **{
    "BG": "#f4ecdc",
    "BG_SIDEBAR": "#ebdfc8",
    "SURFACE": "#faf4e6",
    "SURFACE_2": "#f1e8d4",
    "SURFACE_3": "#e6dac1",
    "BORDER": "#c3b28d",
    "TEXT": "#3a3022",
    "TEXT_MUTED": "#69593d",
    "ACCENT": "#8a5a2b",
    "GOOD": "#2e6b3e",
    "GOOD_BG": "#dcead4",
    "BAD": "#9c3a2e",
    "BAD_BG": "#efd6cd",
    "WARN": "#7a5200",
    "FOCUS": "#3a3022",
    "SIDEBAR_TEXT": "#574a32",
    "SIDEBAR_HOVER": "#e0d2b4",
    "SIDEBAR_TEXT_ACTIVE": "#2a2316",
    "SECONDARY_TEXT": "#3a3022",
    "SECONDARY_HOVER": "#dccfae",
    "SECONDARY_PRESSED": "#d0c19c",
    "DANGER_HOVER": "#e6c3b8",
    "CHOICE_CHECKED_BG": "#e9dcbb",
    "DISABLED_BG": "#e0d5bd",
    "DISABLED_TEXT": "#94886e",
    "PROGRESS_BG": "#e0d5bd",
    "STAFF_PAPER": "#f9f2dd",
    "STAFF_INK": "#3a3022",
    "TOAST_INFO": "#5d4f33",
    "TOAST_SUCCESS": "#3f6b4c",
    "TOAST_WARNING": "#8a5a1f",
    "TOAST_ERROR": "#8a3a30",
})

PALETTES: dict[str, dict[str, str]] = {
    "dark": _DARK,
    "light": _LIGHT,
    "high_contrast": _HIGH_CONTRAST,
    "sepia": _SEPIA,
}

THEME_LABELS = [("Dark", "dark"), ("Light", "light"),
                ("High contrast", "high_contrast"), ("Sepia paper", "sepia")]

# Accent presets offered in Settings. "" = the palette's own accent.
ACCENT_PRESETS = [("Theme default", ""), ("Ocean blue", "#5b8def"),
                  ("Violet", "#7c4dff"), ("Teal", "#14a89c"),
                  ("Rose", "#e25575"), ("Amber", "#e0972a"),
                  ("Green", "#34a853")]


# ---------------------------------------------------------------------------
# Color math (no Qt needed: keeps this importable anywhere, tests included)
# ---------------------------------------------------------------------------

def _rgb(hexcolor: str) -> tuple[int, int, int]:
    h = hexcolor.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _hex(r: float, g: float, b: float) -> str:
    clamp = lambda v: max(0, min(255, int(round(v))))  # noqa: E731
    return f"#{clamp(r):02x}{clamp(g):02x}{clamp(b):02x}"


def _mix(c1: str, c2: str, t: float) -> str:
    """Linear blend of two hex colors, t in [0,1] toward c2."""
    r1, g1, b1 = _rgb(c1)
    r2, g2, b2 = _rgb(c2)
    return _hex(r1 + (r2 - r1) * t, g1 + (g2 - g1) * t, b1 + (b2 - b1) * t)


def _luminance(hexcolor: str) -> float:
    def chan(v: int) -> float:
        v_ = v / 255.0
        return v_ / 12.92 if v_ <= 0.04045 else ((v_ + 0.055) / 1.055) ** 2.4
    r, g, b = _rgb(hexcolor)
    return 0.2126 * chan(r) + 0.7152 * chan(g) + 0.0722 * chan(b)


def contrast_ratio(c1: str, c2: str) -> float:
    l1, l2 = sorted((_luminance(c1), _luminance(c2)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def _text_on(fill: str) -> str:
    """Black-ish or white text, whichever contrasts more with the fill."""
    return "#0f1115" if contrast_ratio(fill, "#0f1115") >= contrast_ratio(fill, "#ffffff") else "#ffffff"


def _derive(palette: dict[str, str], accent_override: str = "") -> dict[str, str]:
    """Resolve a palette + optional accent override into the live token set."""
    tok = dict(palette)
    if accent_override:
        tok["ACCENT"] = accent_override
    accent = tok["ACCENT"]
    tok["ACCENT_HOVER"] = _mix(accent, "#ffffff", 0.16)
    tok["ACCENT_PRESSED"] = _mix(accent, "#000000", 0.22)
    tok["TEXT_DARK"] = _text_on(accent)          # text on accent/success fills
    r, g, b = _rgb(accent)
    tok["ACCENT_SOFT"] = f"rgba({r}, {g}, {b}, 0.18)"
    return tok


# ---------------------------------------------------------------------------
# Live token state (module attributes update on apply_theme)
# ---------------------------------------------------------------------------

TOKENS: dict[str, str] = _derive(_DARK)
CURRENT_THEME = "dark"

# Named attributes used across the UI package. Read these via the module
# (``theme.ACCENT``) so a theme switch is picked up on the next repaint.
ACCENT = TOKENS["ACCENT"]
ACCENT_DIM = TOKENS["ACCENT_PRESSED"]
GOOD = TOKENS["GOOD"]
BAD = TOKENS["BAD"]
WARN = TOKENS["WARN"]
TEXT_MUTED = TOKENS["TEXT_MUTED"]
TEXT_DARK = TOKENS["TEXT_DARK"]
GOOD_BG = TOKENS["GOOD_BG"]
BAD_BG = TOKENS["BAD_BG"]
SURFACE = TOKENS["SURFACE"]
BORDER = TOKENS["BORDER"]
STAFF_PAPER = TOKENS["STAFF_PAPER"]
STAFF_INK = TOKENS["STAFF_INK"]
TOAST_COLORS = {
    "info": TOKENS["TOAST_INFO"],
    "success": TOKENS["TOAST_SUCCESS"],
    "warning": TOKENS["TOAST_WARNING"],
    "error": TOKENS["TOAST_ERROR"],
}


def set_palette(name: str, accent_override: str = "") -> None:
    """Switch the live token set. Safe to call before any Qt object exists."""
    global TOKENS, CURRENT_THEME, ACCENT, ACCENT_DIM, GOOD, BAD, WARN
    global TEXT_MUTED, TEXT_DARK, GOOD_BG, BAD_BG, SURFACE, BORDER
    global STAFF_PAPER, STAFF_INK, TOAST_COLORS
    palette = PALETTES.get(name)
    if palette is None:
        name, palette = "dark", _DARK
    TOKENS = _derive(palette, accent_override)
    CURRENT_THEME = name
    ACCENT = TOKENS["ACCENT"]
    ACCENT_DIM = TOKENS["ACCENT_PRESSED"]
    GOOD = TOKENS["GOOD"]
    BAD = TOKENS["BAD"]
    WARN = TOKENS["WARN"]
    TEXT_MUTED = TOKENS["TEXT_MUTED"]
    TEXT_DARK = TOKENS["TEXT_DARK"]
    GOOD_BG = TOKENS["GOOD_BG"]
    BAD_BG = TOKENS["BAD_BG"]
    SURFACE = TOKENS["SURFACE"]
    BORDER = TOKENS["BORDER"]
    STAFF_PAPER = TOKENS["STAFF_PAPER"]
    STAFF_INK = TOKENS["STAFF_INK"]
    TOAST_COLORS = {
        "info": TOKENS["TOAST_INFO"],
        "success": TOKENS["TOAST_SUCCESS"],
        "warning": TOKENS["TOAST_WARNING"],
        "error": TOKENS["TOAST_ERROR"],
    }


# ---------------------------------------------------------------------------
# Stylesheet
# ---------------------------------------------------------------------------

_QSS_TEMPLATE = """
* {{ font-family: "Segoe UI", "Inter", sans-serif; font-size: {fs14}px; }}
QMainWindow, QWidget {{ background: %BG%; color: %TEXT%; }}
QLabel {{ color: %TEXT%; background: transparent; }}
QLabel#H1 {{ font-size: {fs24}px; font-weight: 800; }}
QLabel#H2 {{ font-size: {fs20}px; font-weight: 800; }}
QLabel#H3 {{ font-size: {fs16}px; font-weight: 700; }}
QLabel#BodyLg {{ font-size: {fs16}px; }}
QLabel#Kicker {{ color: %ACCENT_TEXT%; font-size: {fs12}px; font-weight: 700; letter-spacing: 1px; }}
QLabel#StatValue {{ font-size: {fs26}px; font-weight: 800; }}
QLabel#Prompt {{ font-size: {fs20}px; font-weight: 700; }}
QLabel#Subtle {{ color: %TEXT_MUTED%; }}
QLabel#Badge {{ color: %TEXT_MUTED%; font-size: {fs12}px; font-weight: 600; letter-spacing: 1px; }}
QLabel#Hint {{ color: %WARN%; }}
QLabel#AccentValue {{ color: %ACCENT_TEXT%; font-weight: 700; }}

#Sidebar {{ background: %BG_SIDEBAR%; }}
#Sidebar QPushButton {{
    text-align: left; padding: 10px 16px; border: 2px solid transparent;
    border-radius: 8px; color: %SIDEBAR_TEXT%; background: transparent;
    font-size: {fs14}px;
}}
#Sidebar QPushButton:hover {{ background: %SIDEBAR_HOVER%; color: %SIDEBAR_TEXT_ACTIVE%; }}
#Sidebar QPushButton:focus {{ border-color: %FOCUS%; }}
#Sidebar QPushButton:checked {{
    background: %ACCENT_SOFT%; color: %SIDEBAR_TEXT_ACTIVE%; font-weight: 600;
    border-left: 3px solid %ACCENT%;
}}
#Brand {{ font-size: {fs18}px; font-weight: 700; color: %SIDEBAR_TEXT_ACTIVE%; padding: 14px 16px; }}

QPushButton {{
    background: %ACCENT%; color: %TEXT_DARK%; border: 2px solid transparent;
    border-radius: 8px; padding: 8px 15px; font-weight: 600;
}}
QPushButton:hover {{ background: %ACCENT_HOVER%; }}
QPushButton:pressed {{ background: %ACCENT_PRESSED%; }}
QPushButton:focus {{ border-color: %FOCUS%; }}
QPushButton:disabled {{ background: %DISABLED_BG%; color: %DISABLED_TEXT%; }}
QPushButton#Secondary {{ background: %SURFACE_3%; color: %SECONDARY_TEXT%; }}
QPushButton#Secondary:hover {{ background: %SECONDARY_HOVER%; }}
QPushButton#Secondary:pressed {{ background: %SECONDARY_PRESSED%; }}
QPushButton#Danger {{ background: %BAD_BG%; color: %BAD%; border: 1px solid %BAD%; }}
QPushButton#Danger:hover {{ background: %DANGER_HOVER%; }}
QPushButton#Choice {{
    background: %SURFACE_2%; color: %TEXT%; border: 2px solid %BORDER%;
    text-align: left; padding: 11px 15px; font-weight: 500;
}}
QPushButton#Choice:hover {{ border-color: %ACCENT%; }}
QPushButton#Choice:focus {{ border-color: %FOCUS%; }}
QPushButton#Choice:checked {{ border-color: %ACCENT%; background: %CHOICE_CHECKED_BG%; }}
QPushButton#Choice:disabled {{ background: %SURFACE_2%; color: %TEXT_MUTED%; border-color: %BORDER%; }}
QPushButton#Choice[result="correct"] {{
    background: %GOOD%; color: %TEXT_ON_GOOD%; border-color: %GOOD%; font-weight: 700;
}}
QPushButton#Choice[result="wrong"] {{
    background: %BAD_BG%; color: %TEXT%; border-color: %BAD%;
}}

QFrame#Card {{ background: %SURFACE%; border: 1px solid %BORDER%; border-radius: 12px; }}
QFrame#FeedbackGood {{ background: %GOOD_BG%; border: 1px solid %GOOD%; border-radius: 10px; }}
QFrame#FeedbackBad {{ background: %BAD_BG%; border: 1px solid %BAD%; border-radius: 10px; }}
QFrame#NavDivider {{ background: %BORDER%; max-height: 1px; border: none; }}

QProgressBar {{ background: %PROGRESS_BG%; border: none; border-radius: 6px; height: 10px; text-align: center; }}
QProgressBar::chunk {{ background: %ACCENT%; border-radius: 6px; }}
QComboBox, QLineEdit, QSpinBox {{
    background: %SURFACE_2%; border: 1px solid %BORDER%; border-radius: 6px; padding: 6px 8px;
}}
QComboBox:focus, QLineEdit:focus, QSpinBox:focus {{ border: 1px solid %ACCENT%; }}
QComboBox QAbstractItemView {{ background: %SURFACE_2%; selection-background-color: %ACCENT%; selection-color: %TEXT_DARK%; }}
QScrollArea {{ border: none; }}
QTabWidget::pane {{ border: 1px solid %BORDER%; border-radius: 8px; top: -1px; }}
QTabBar::tab {{
    background: %SURFACE_2%; color: %TEXT_MUTED%; padding: 7px 16px;
    border: 1px solid %BORDER%; border-bottom: none; margin-right: 2px;
    border-top-left-radius: 6px; border-top-right-radius: 6px;
}}
QTabBar::tab:selected {{ background: %SURFACE%; color: %TEXT%; border-bottom: 2px solid %ACCENT%; }}
QTabBar::tab:hover {{ color: %TEXT%; }}
QSlider::groove:horizontal {{ height: 6px; background: %BORDER%; border-radius: 3px; }}
QSlider::handle:horizontal {{ background: %ACCENT%; width: 20px; margin: -7px 0; border-radius: 10px; }}
QSlider:focus::handle:horizontal {{ background: %FOCUS%; }}
"""


def _build_qss(scale: float = 1.0, tokens: dict[str, str] | None = None) -> str:
    tok = dict(tokens or TOKENS)
    # Accent used *as text* on BG must stay readable; nudge it toward TEXT
    # until it clears WCAG AA (matters for light themes with light accents).
    accent_text = tok["ACCENT"]
    for _ in range(6):
        if contrast_ratio(accent_text, tok["BG"]) >= 4.5:
            break
        accent_text = _mix(accent_text, tok["TEXT"], 0.25)
    tok["ACCENT_TEXT"] = accent_text
    tok["TEXT_ON_GOOD"] = _text_on(tok["GOOD"])
    sizes = {f"fs{n}": max(10, round(n * scale)) for n in (12, 14, 16, 18, 20, 24, 26)}
    qss = _QSS_TEMPLATE.format(**sizes)
    for key, value in sorted(tok.items(), key=lambda kv: -len(kv[0])):
        qss = qss.replace(f"%{key}%", value)
    return qss


DARK_QSS = _build_qss()


def compute_scale(app, settings=None) -> float:
    """Explicit ui_scale setting when set (>0), else the system-font factor."""
    if settings is not None:
        try:
            explicit = float(settings.get("ui_scale", 0.0))
        except Exception:  # noqa: BLE001
            explicit = 0.0
        if explicit > 0:
            return max(0.9, min(2.0, explicit))
    try:
        base_pt = float(app.font().pointSizeF())
    except Exception:  # noqa: BLE001 - never let theming break startup
        base_pt = -1.0
    scale = (base_pt / 9.0) if base_pt > 0 else 1.0
    return max(0.9, min(2.0, scale))


def apply_theme(app, settings=None) -> None:
    """Apply the user's theme/accent/scale (or the defaults) app-wide.

    Idempotent and safe to call again at runtime: rebuilds the stylesheet and
    refreshes this module's live color attributes.
    """
    name, accent = "dark", ""
    if settings is not None:
        try:
            name = str(settings.get("theme", "dark"))
            accent = str(settings.get("accent_color", ""))
        except Exception:  # noqa: BLE001
            name, accent = "dark", ""
    if accent and not (len(accent) == 7 and accent.startswith("#")):
        accent = ""
    set_palette(name, accent)
    app.setStyleSheet(_build_qss(compute_scale(app, settings)))
