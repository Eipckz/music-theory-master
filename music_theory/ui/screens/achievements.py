"""Achievements gallery: every achievement with locked/unlocked state and
unlock dates, grouped unlocked-first."""

from __future__ import annotations

import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame, QGridLayout, QLabel, QScrollArea, QVBoxLayout, QWidget,
)

from ...achievements import ACHIEVEMENTS
from ..common import heading, subtle


class AchievementsScreen(QWidget):
    def __init__(self, ctx, parent=None) -> None:
        super().__init__(parent)
        self.ctx = ctx
        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 20)
        outer.setSpacing(10)
        outer.addWidget(heading("Achievements"))
        self.progress = subtle("")
        outer.addWidget(self.progress)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        host = QWidget()
        self.grid = QGridLayout(host)
        self.grid.setSpacing(12)
        scroll.setWidget(host)
        outer.addWidget(scroll, 1)
        self.refresh()

    def on_show(self) -> None:
        self.refresh()

    def refresh(self) -> None:
        while self.grid.count():
            w = self.grid.takeAt(0).widget()
            if w:
                w.setParent(None)
        unlocked = self.ctx.db.achievements_with_dates()
        self.progress.setText(
            f"{len(unlocked)} of {len(ACHIEVEMENTS)} unlocked. "
            "Locked ones show how to earn them.")
        # unlocked first (most recent first), then locked in definition order
        ordered = sorted(unlocked, key=lambda k: -unlocked[k])
        ordered += [k for k in ACHIEVEMENTS if k not in unlocked]
        for i, key in enumerate(ordered):
            title, desc = ACHIEVEMENTS.get(key, (key, ""))
            self.grid.addWidget(self._tile(key, title, desc, unlocked.get(key)),
                                i // 2, i % 2)
        self.grid.setRowStretch(self.grid.rowCount(), 1)

    def _tile(self, key: str, title: str, desc: str, ts: float | None) -> QFrame:
        tile = QFrame()
        tile.setObjectName("Card")
        lay = QVBoxLayout(tile)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(2)
        icon = "🏆" if ts else "🔒"
        head = QLabel(f"{icon}  <b>{title}</b>")
        head.setTextFormat(Qt.TextFormat.RichText)
        lay.addWidget(head)
        body = subtle(desc)
        body.setWordWrap(True)
        lay.addWidget(body)
        if ts:
            when = datetime.date.fromtimestamp(ts).strftime("%b %d, %Y")
            lay.addWidget(subtle(f"Unlocked {when}"))
            tile.setAccessibleName(f"Achievement unlocked: {title}. {desc}")
        else:
            tile.setAccessibleName(f"Achievement locked: {title}. {desc}")
        return tile
