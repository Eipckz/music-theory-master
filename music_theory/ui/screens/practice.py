"""Free-practice workspace: drill any exercise type at any difficulty. Results
feed the same mastery model as coursework, so gains here raise course
difficulty (and weak spots resurface) - the requested cross-feature loop."""

from __future__ import annotations

import random

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QHBoxLayout, QLabel, QPushButton, QSlider, QVBoxLayout, QWidget,
)

from ...adaptive import MasteryModel, difficulty_for_rating, level_for_rating
from ...errors import guard
from ...exercises.registry import all_types, safe_generate, title_of, types_for_domain, domain_of
from ..common import heading, subtle
from ..exercise_player import ExercisePlayer
from ..theme import TEXT_MUTED

_DOMAINS = [("All", ""), ("Theory", "theory"), ("Aural", "aural"), ("Piano", "piano")]


class PracticeScreen(QWidget):
    def __init__(self, ctx, parent=None) -> None:
        super().__init__(parent)
        self.ctx = ctx
        self.rng = random.Random()
        self._loaded = False
        self._adaptive_diff: dict[str, float] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 16)
        root.setSpacing(12)
        root.addWidget(heading("Practice"))
        root.addWidget(subtle("Pick a topic - difficulty adapts automatically as you go: it rises "
                              "when you're right and eases when you're not. Everything here updates "
                              "your mastery, so the course adapts too."))

        controls = QHBoxLayout()
        self.domain_combo = QComboBox()
        self.domain_combo.setAccessibleName("Practice area")
        for label, _ in _DOMAINS:
            self.domain_combo.addItem(label)
        self.domain_combo.currentIndexChanged.connect(self._refill_types)
        controls.addWidget(QLabel("Area:"))
        controls.addWidget(self.domain_combo)

        self.type_combo = QComboBox()
        self.type_combo.setAccessibleName("Practice topic")
        controls.addWidget(QLabel("Topic:"))
        controls.addWidget(self.type_combo, 1)

        self.adaptive_chk = QCheckBox("Adaptive")
        self.adaptive_chk.setChecked(True)
        self.adaptive_chk.setToolTip("Automatically raise or lower difficulty based on your answers.")
        self.adaptive_chk.toggled.connect(self._on_adaptive_toggled)
        controls.addWidget(self.adaptive_chk)

        self.diff = QSlider(Qt.Orientation.Horizontal)
        self.diff.setAccessibleName("Difficulty")
        self.diff.setMinimum(0)
        self.diff.setMaximum(20)
        self.diff.setValue(6)
        self.diff_label = QLabel("Difficulty 3.0")
        self.diff.valueChanged.connect(self._on_slider_changed)
        controls.addWidget(self.diff_label)
        controls.addWidget(self.diff, 1)

        start = QPushButton("New")
        start.clicked.connect(self._new)
        controls.addWidget(start)
        root.addLayout(controls)

        self.player = ExercisePlayer(self.ctx.engine, self.ctx.midi,
                                     settings=self.ctx.settings)
        root.addWidget(self.player, 1)
        self._refill_types()
        self._on_adaptive_toggled(self.adaptive_chk.isChecked())

    def _refill_types(self) -> None:
        _, dom = _DOMAINS[self.domain_combo.currentIndex()]
        types = types_for_domain(dom) if dom else all_types()
        self.type_combo.blockSignals(True)
        self.type_combo.clear()
        for et in types:
            self.type_combo.addItem(title_of(et), et)
        self.type_combo.blockSignals(False)

    def preset(self, *, domain: str = "", etype: str = "") -> None:
        if domain:
            for i, (_, d) in enumerate(_DOMAINS):
                if d == domain:
                    self.domain_combo.setCurrentIndex(i)
                    break
        self._refill_types()
        if etype:
            idx = self.type_combo.findData(etype)
            if idx >= 0:
                self.type_combo.setCurrentIndex(idx)
        self._new()

    def on_show(self) -> None:
        if not self._loaded:
            self._new()
            self._loaded = True

    # -- adaptive difficulty ----------------------------------------------
    def _on_adaptive_toggled(self, on: bool) -> None:
        self.diff.setEnabled(not on)
        self.diff_label.setStyleSheet("" if not on else f"color:{TEXT_MUTED};")

    def _on_slider_changed(self, v: int) -> None:
        self.diff_label.setText(f"Difficulty {v/2:.1f}")
        if self.adaptive_chk.isChecked():
            etype = self.type_combo.currentData()
            if etype:
                self._adaptive_diff[etype] = v / 2.0  # manual override seed

    def _skill_for_etype(self, etype: str):
        for s in self.ctx.curriculum:
            if etype in s.etypes:
                return s
        return None

    def _seed_difficulty(self, etype: str) -> float:
        skill = self._skill_for_etype(etype)
        if skill is None:
            return self.diff.value() / 2.0
        lo, hi = skill.diff_range
        m = self.ctx.db.get_mastery(skill.id)
        base = difficulty_for_rating(m["rating"]) if m and m.get("n_attempts", 0) else lo + 1.0
        return max(lo, min(hi, base))

    def _current_difficulty(self, etype: str) -> float:
        if not self.adaptive_chk.isChecked():
            return self.diff.value() / 2.0
        if etype not in self._adaptive_diff:
            self._adaptive_diff[etype] = self._seed_difficulty(etype)
        return self._adaptive_diff[etype]

    def _reflect_difficulty(self, difficulty: float) -> None:
        self.diff.blockSignals(True)
        self.diff.setValue(int(round(difficulty * 2)))
        self.diff.blockSignals(False)
        self.diff_label.setText(f"Difficulty {difficulty:.1f}")

    def _adjust_difficulty(self, etype: str, correct: bool, response_ms: int) -> None:
        skill = self._skill_for_etype(etype)
        lo, hi = skill.diff_range if skill else (0.0, 10.0)
        cur = self._adaptive_diff.get(etype, self._seed_difficulty(etype))
        if correct:
            step = 0.6 + (0.3 if 0 < response_ms < 8000 else 0.0)
        else:
            step = -0.9
        self._adaptive_diff[etype] = max(lo, min(hi, cur + step))

    # -- exercise flow ----------------------------------------------------
    @guard("Practice._new")
    def _new(self) -> None:
        etype = self.type_combo.currentData()
        if not etype:
            return
        difficulty = self._current_difficulty(etype)
        self._reflect_difficulty(difficulty)
        ex = safe_generate(etype, difficulty, self.rng)
        self.player.set_exercise(ex, on_answer=self._on_answer, on_next=self._new,
                                 badge=f"Practice  \u00b7  {title_of(etype)}  \u00b7  "
                                       f"difficulty {difficulty:.1f}")

    @guard("Practice._on_answer")
    def _on_answer(self, correct: bool, response_ms: int) -> None:
        ex = self.player.ex
        if ex is None:
            return
        domain_ids = [s.id for s in self.ctx.curriculum.by_domain(ex.domain) if s.schedulable]
        before_level = level_for_rating(MasteryModel.overall_rating(self.ctx.db, domain_ids))
        before_mastered = self.ctx.curriculum.is_mastered(self.ctx.db, ex.skill_id)

        self.ctx.scheduler.record(ex.skill_id, correct, difficulty=ex.difficulty,
                                  domain=ex.domain, etype=ex.etype,
                                  response_ms=response_ms, source="practice")
        xp = (5 if correct else 1)
        if correct and self.player.was_hinted:
            xp = 3
        self.ctx.db.add_xp(xp)

        if self.adaptive_chk.isChecked():
            self._adjust_difficulty(ex.etype, correct, response_ms)

        after_level = level_for_rating(MasteryModel.overall_rating(self.ctx.db, domain_ids))
        after_mastered = self.ctx.curriculum.is_mastered(self.ctx.db, ex.skill_id)
        if after_mastered and not before_mastered:
            skill = self.ctx.curriculum.get(ex.skill_id)
            self._notify(f"\u2b50 Skill mastered: {skill.title if skill else ex.skill_id}!",
                         kind="success")
        elif after_level != before_level:
            self._notify(f"\U0001F389 Level up! {ex.domain.title()} is now {after_level}.",
                         kind="success")

    def _notify(self, message: str, *, kind: str = "info") -> None:
        win = self.window()
        if hasattr(win, "toast"):
            win.toast(message, kind=kind)
