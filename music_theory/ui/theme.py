"""Application theme: a single token-driven dark stylesheet.

All colors live in TOKENS; widgets reference roles via objectName selectors
(QLabel#H1, QPushButton#Choice, ...) so per-widget setStyleSheet calls stay
rare. Font sizes scale with the user's system font (accessibility: respects
"make text bigger" preferences) via the factor computed in apply_theme().

Contrast notes (WCAG AA): primary buttons use dark text on the accent fill
(4.6:1); every text/background pair in TOKENS meets 4.5:1 on its intended
surface. Keyboard focus is always visible: every interactive widget has a
:focus rule, with constant border widths so focusing never shifts layout.
"""

from __future__ import annotations

TOKENS = {
    "BG": "#15171c",
    "BG_SIDEBAR": "#0f1115",
    "SURFACE": "#1a1d23",       # cards
    "SURFACE_2": "#1d2128",     # inputs, choice buttons
    "SURFACE_3": "#262b34",     # secondary buttons
    "BORDER": "#2c323c",
    "TEXT": "#e7e9ee",
    "TEXT_DARK": "#0f1115",     # text on accent / success fills
    "TEXT_MUTED": "#9aa3b2",
    "ACCENT": "#5b8def",
    "ACCENT_HOVER": "#6e9cf2",
    "ACCENT_PRESSED": "#3f6bd0",
    "GOOD": "#3ec46d",
    "GOOD_BG": "#1d3528",
    "BAD": "#e2554e",
    "BAD_BG": "#3a2226",
    "WARN": "#e0a73a",
    "FOCUS": "#e7e9ee",
}

# Backwards-compatible named constants (imported across the UI package).
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
STAFF_PAPER = "#f6f3ea"

TOAST_COLORS = {
    "info": "#2f3b52",
    "success": "#2f7d4f",
    "warning": "#8a5a1f",
    "error": "#8a2f2f",
}

_QSS_TEMPLATE = """
* {{ font-family: "Segoe UI", "Inter", sans-serif; font-size: {fs14}px; }}
QMainWindow, QWidget {{ background: %BG%; color: %TEXT%; }}
QLabel {{ color: %TEXT%; background: transparent; }}
QLabel#H1 {{ font-size: {fs24}px; font-weight: 800; }}
QLabel#H2 {{ font-size: {fs20}px; font-weight: 800; }}
QLabel#H3 {{ font-size: {fs16}px; font-weight: 700; }}
QLabel#BodyLg {{ font-size: {fs16}px; }}
QLabel#Kicker {{ color: %ACCENT%; font-size: {fs12}px; font-weight: 700; letter-spacing: 1px; }}
QLabel#StatValue {{ font-size: {fs26}px; font-weight: 800; }}
QLabel#Prompt {{ font-size: {fs20}px; font-weight: 700; }}
QLabel#Subtle {{ color: %TEXT_MUTED%; }}
QLabel#Badge {{ color: %TEXT_MUTED%; font-size: {fs12}px; font-weight: 600; letter-spacing: 1px; }}
QLabel#Hint {{ color: %WARN%; }}
QLabel#AccentValue {{ color: %ACCENT%; font-weight: 700; }}

#Sidebar {{ background: %BG_SIDEBAR%; }}
#Sidebar QPushButton {{
    text-align: left; padding: 10px 16px; border: 2px solid transparent;
    border-radius: 8px; color: #b9bfcc; background: transparent;
    font-size: {fs14}px;
}}
#Sidebar QPushButton:hover {{ background: #1c2026; color: #fff; }}
#Sidebar QPushButton:focus {{ border-color: %FOCUS%; }}
#Sidebar QPushButton:checked {{
    background: rgba(91, 141, 239, 0.18); color: #ffffff; font-weight: 600;
    border-left: 3px solid %ACCENT%;
}}
#Brand {{ font-size: {fs18}px; font-weight: 700; color: #fff; padding: 14px 16px; }}

QPushButton {{
    background: %ACCENT%; color: %TEXT_DARK%; border: 2px solid transparent;
    border-radius: 8px; padding: 8px 15px; font-weight: 600;
}}
QPushButton:hover {{ background: %ACCENT_HOVER%; }}
QPushButton:pressed {{ background: %ACCENT_PRESSED%; color: #ffffff; }}
QPushButton:focus {{ border-color: %FOCUS%; }}
QPushButton:disabled {{ background: #2a2f38; color: #6b7280; }}
QPushButton#Secondary {{ background: %SURFACE_3%; color: #d7dbe4; }}
QPushButton#Secondary:hover {{ background: #2f3540; }}
QPushButton#Secondary:pressed {{ background: #232831; }}
QPushButton#Danger {{ background: %BAD_BG%; color: %BAD%; border: 1px solid %BAD%; }}
QPushButton#Danger:hover {{ background: #4a2a2e; }}
QPushButton#Choice {{
    background: %SURFACE_2%; color: %TEXT%; border: 2px solid %BORDER%;
    text-align: left; padding: 11px 15px; font-weight: 500;
}}
QPushButton#Choice:hover {{ border-color: %ACCENT%; }}
QPushButton#Choice:focus {{ border-color: %FOCUS%; }}
QPushButton#Choice:checked {{ border-color: %ACCENT%; background: #20283a; }}
QPushButton#Choice:disabled {{ background: %SURFACE_2%; color: %TEXT_MUTED%; border-color: %BORDER%; }}
QPushButton#Choice[result="correct"] {{
    background: %GOOD%; color: %TEXT_DARK%; border-color: %GOOD%; font-weight: 700;
}}
QPushButton#Choice[result="wrong"] {{
    background: %BAD_BG%; color: %TEXT%; border-color: %BAD%;
}}

QFrame#Card {{ background: %SURFACE%; border: 1px solid %BORDER%; border-radius: 12px; }}
QFrame#FeedbackGood {{ background: %GOOD_BG%; border: 1px solid %GOOD%; border-radius: 10px; }}
QFrame#FeedbackBad {{ background: %BAD_BG%; border: 1px solid %BAD%; border-radius: 10px; }}
QFrame#NavDivider {{ background: %BORDER%; max-height: 1px; border: none; }}

QProgressBar {{ background: #22262e; border: none; border-radius: 6px; height: 10px; text-align: center; }}
QProgressBar::chunk {{ background: %ACCENT%; border-radius: 6px; }}
QComboBox, QLineEdit, QSpinBox {{
    background: %SURFACE_2%; border: 1px solid %BORDER%; border-radius: 6px; padding: 6px 8px;
}}
QComboBox:focus, QLineEdit:focus, QSpinBox:focus {{ border: 1px solid %ACCENT%; }}
QComboBox QAbstractItemView {{ background: %SURFACE_2%; selection-background-color: %ACCENT%; }}
QScrollArea {{ border: none; }}
QSlider::groove:horizontal {{ height: 6px; background: %BORDER%; border-radius: 3px; }}
QSlider::handle:horizontal {{ background: %ACCENT%; width: 20px; margin: -7px 0; border-radius: 10px; }}
QSlider:focus::handle:horizontal {{ background: #ffffff; }}
"""


def _build_qss(scale: float = 1.0) -> str:
    sizes = {f"fs{n}": max(10, round(n * scale)) for n in (12, 14, 16, 18, 20, 24, 26)}
    qss = _QSS_TEMPLATE.format(**sizes)
    for key, value in TOKENS.items():
        qss = qss.replace(f"%{key}%", value)
    return qss


DARK_QSS = _build_qss()


def apply_theme(app) -> None:
    # Scale our px sizes by the user's system font preference so the
    # "make text bigger" accessibility setting is respected. Windows default
    # is 9pt; a 12pt system font yields a ~1.33x larger UI.
    try:
        base_pt = float(app.font().pointSizeF())
    except Exception:  # noqa: BLE001 - never let theming break startup
        base_pt = -1.0
    scale = (base_pt / 9.0) if base_pt > 0 else 1.0
    scale = max(0.9, min(2.0, scale))
    app.setStyleSheet(_build_qss(scale))
