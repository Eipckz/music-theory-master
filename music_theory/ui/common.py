"""Small shared UI helpers."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


def card(title: str = "") -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName("Card")
    lay = QVBoxLayout(frame)
    lay.setContentsMargins(18, 16, 18, 16)
    lay.setSpacing(10)
    if title:
        lay.addWidget(card_title(title))
    return frame, lay


def card_title(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("H3")
    return lbl


def heading(text: str, size: int = 24) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("H1")
    return lbl


def subtle(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("Subtle")
    lbl.setWordWrap(True)
    return lbl
