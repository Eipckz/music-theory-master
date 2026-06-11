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
        lbl = QLabel(title)
        lbl.setStyleSheet("font-size:16px; font-weight:700;")
        lay.addWidget(lbl)
    return frame, lay


def heading(text: str, size: int = 24) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(f"font-size:{size}px; font-weight:800;")
    return lbl


def subtle(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet("color:#8b93a3;")
    lbl.setWordWrap(True)
    return lbl
