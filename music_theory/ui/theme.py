"""Application theme (dark, with an accent palette)."""

from __future__ import annotations

ACCENT = "#5b8def"
ACCENT_DIM = "#3f6bd0"
GOOD = "#3ec46d"
BAD = "#e2554e"
WARN = "#e0a73a"

DARK_QSS = f"""
* {{ font-family: "Segoe UI", "Inter", sans-serif; font-size: 14px; }}
QMainWindow, QWidget {{ background: #15171c; color: #e7e9ee; }}
QLabel {{ color: #e7e9ee; }}
#Sidebar {{ background: #0f1115; }}
#Sidebar QPushButton {{
    text-align: left; padding: 10px 16px; border: none; border-radius: 8px;
    color: #b9bfcc; background: transparent; font-size: 14px;
}}
#Sidebar QPushButton:hover {{ background: #1c2026; color: #fff; }}
#Sidebar QPushButton:checked {{ background: {ACCENT}; color: white; font-weight: 600; }}
#Brand {{ font-size: 18px; font-weight: 700; color: #fff; padding: 14px 16px; }}
QPushButton {{
    background: {ACCENT}; color: white; border: none; border-radius: 8px;
    padding: 9px 16px; font-weight: 600;
}}
QPushButton:hover {{ background: {ACCENT_DIM}; }}
QPushButton:disabled {{ background: #2a2f38; color: #6b7280; }}
QPushButton#Secondary {{ background: #262b34; color: #d7dbe4; }}
QPushButton#Secondary:hover {{ background: #2f3540; }}
QPushButton#Choice {{
    background: #1d2128; color: #e7e9ee; border: 1px solid #2c323c;
    text-align: left; padding: 12px 16px; font-weight: 500;
}}
QPushButton#Choice:hover {{ border-color: {ACCENT}; }}
QFrame#Card {{ background: #1a1d23; border: 1px solid #252a32; border-radius: 12px; }}
QProgressBar {{ background: #22262e; border: none; border-radius: 6px; height: 10px; text-align: center; }}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 6px; }}
QComboBox, QLineEdit, QSpinBox {{
    background: #1d2128; border: 1px solid #2c323c; border-radius: 6px; padding: 6px 8px;
}}
QComboBox QAbstractItemView {{ background: #1d2128; selection-background-color: {ACCENT}; }}
QScrollArea {{ border: none; }}
QSlider::groove:horizontal {{ height: 6px; background: #2c323c; border-radius: 3px; }}
QSlider::handle:horizontal {{ background: {ACCENT}; width: 14px; margin: -5px 0; border-radius: 7px; }}
"""


def apply_theme(app) -> None:
    app.setStyleSheet(DARK_QSS)
