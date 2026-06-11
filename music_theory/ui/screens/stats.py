"""Progress & mastery map: every skill, its mastery, and unlock state."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QProgressBar, QScrollArea, QVBoxLayout, QWidget,
)

from ...adaptive import difficulty_for_rating
from ...curriculum import LEVEL_ORDER
from ..common import card, heading, subtle


class StatsScreen(QWidget):
    def __init__(self, ctx, parent=None) -> None:
        super().__init__(parent)
        self.ctx = ctx
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 12)
        root.addWidget(heading("Progress & Mastery Map"))
        self.summary = subtle("")
        root.addWidget(self.summary)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.inner = QWidget()
        self.inner_layout = QVBoxLayout(self.inner)
        self.inner_layout.setContentsMargins(0, 8, 0, 8)
        self.inner_layout.setSpacing(14)
        self.scroll.setWidget(self.inner)
        root.addWidget(self.scroll, 1)

    def on_show(self) -> None:
        while self.inner_layout.count():
            w = self.inner_layout.takeAt(0).widget()
            if w:
                w.setParent(None)

        n, c = self.ctx.db.attempt_counts()
        summ = self.ctx.scheduler.progress_summary()
        self.summary.setText(
            f"{summ['mastered']}/{summ['total']} skills mastered  \u00b7  "
            f"{summ['unlocked']} unlocked  \u00b7  {n} exercises answered  \u00b7  "
            f"{int(100*c/n) if n else 0}% lifetime accuracy")

        for level in LEVEL_ORDER:
            skills = [s for s in self.ctx.curriculum.by_level(level)]
            if not skills:
                continue
            frame, lay = card(level)
            for s in skills:
                lay.addWidget(self._skill_row(s))
            self.inner_layout.addWidget(frame)
        self.inner_layout.addStretch(1)

    def _skill_row(self, skill) -> QWidget:
        m = self.ctx.db.get_mastery(skill.id) or {}
        prob = float(m.get("mastery_prob", 0.0))
        attempts = int(m.get("n_attempts", 0))
        unlocked = bool(m.get("unlocked", 0)) or self.ctx.curriculum.is_unlocked(self.ctx.db, skill.id)
        mastered = self.ctx.curriculum.is_mastered(self.ctx.db, skill.id)

        holder = QWidget()
        row = QHBoxLayout(holder)
        row.setContentsMargins(0, 2, 0, 2)
        name = QLabel(skill.title + ("  \U0001F512" if not unlocked else ""))
        name.setMinimumWidth(230)
        if skill.guided:
            name.setText(skill.title + "  (guided)")
        row.addWidget(name)

        bar = QProgressBar()
        bar.setMaximum(100)
        bar.setValue(int(prob * 100))
        bar.setTextVisible(False)
        bar.setFixedHeight(10)
        row.addWidget(bar, 1)

        if skill.guided:
            tag = "self-study"
        elif mastered:
            tag = "mastered"
        elif attempts:
            tag = f"lvl {difficulty_for_rating(m.get('rating', 1000)):.1f} \u00b7 {attempts} tries"
        else:
            tag = "not started"
        lab = QLabel(tag)
        lab.setStyleSheet("color:#8b93a3; font-size:12px;")
        lab.setMinimumWidth(120)
        lab.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(lab)
        return holder
