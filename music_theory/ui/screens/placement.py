"""Adaptive placement test screen: estimates the learner's level per domain,
then seeds the curriculum so coursework starts at the right difficulty."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout, QWidget,
)

from ...adaptive import PlacementTest
from ...errors import guard
from ..common import card, heading, subtle
from ..exercise_player import ExercisePlayer


class PlacementScreen(QWidget):
    def __init__(self, ctx, parent=None) -> None:
        super().__init__(parent)
        self.ctx = ctx
        self.navigate = None
        self.pt = None
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 20)
        root.setSpacing(14)
        root.addWidget(heading("Placement Test"))

        self.intro = self._build_intro()
        root.addWidget(self.intro)

        self.test_area = QWidget()
        ta = QVBoxLayout(self.test_area)
        ta.setContentsMargins(0, 0, 0, 0)
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        ta.addWidget(self.progress)
        self.domain_label = subtle("")
        ta.addWidget(self.domain_label)
        self.player = ExercisePlayer(self.ctx.engine, self.ctx.midi)
        ta.addWidget(self.player, 1)
        self.test_area.hide()
        root.addWidget(self.test_area, 1)

        self.results = QWidget()
        self.results_layout = QVBoxLayout(self.results)
        self.results_layout.setContentsMargins(0, 0, 0, 0)
        self.results.hide()
        root.addWidget(self.results)
        root.addStretch(0)
        self._reset_to_intro()

    def _build_intro(self) -> QWidget:
        frame, lay = card("How it works")
        lay.addWidget(subtle(
            "Answer a short, adapting set of questions across theory, aural skills, "
            "and piano. Difficulty climbs while you keep answering correctly and eases "
            "when you miss, then the test double-checks your level with a couple of "
            "confirmation questions - so the result is a level you're truly secure at, "
            "never an inflated one. Your results unlock the right starting point in "
            "the course, and you can always climb quickly by doing well in lessons."))
        row = QHBoxLayout()
        self.start_btn = QPushButton("Start placement")
        self.start_btn.clicked.connect(self._start)
        row.addWidget(self.start_btn)
        row.addStretch(1)
        lay.addLayout(row)
        return frame

    def _reset_to_intro(self) -> None:
        """Restore the intro/start view so the test can always be (re)started."""
        self.pt = None
        prior = self.ctx.db.latest_placement()
        self.start_btn.setText("Retake placement test" if prior else "Start placement")
        self.test_area.hide()
        self.results.hide()
        self.intro.show()

    def on_show(self) -> None:
        if self.pt is None:
            self._reset_to_intro()

    @guard("Placement._start")
    def _start(self) -> None:
        self.pt = PlacementTest()
        self.intro.hide()
        self.results.hide()
        self.test_area.show()
        self._load_next()

    @guard("Placement._load_next")
    def _load_next(self) -> None:
        ex = self.pt.next_item()
        done, total = self.pt.progress
        self.progress.setMaximum(total)
        self.progress.setValue(done)
        if ex is None:
            self._finish()
            return
        dom = self.pt.current_domain
        self.domain_label.setText(f"Assessing: <b>{dom.title()}</b>")
        self.player.set_exercise(ex, on_answer=self._on_answer, show_next=False)

    @guard("Placement._on_answer")
    def _on_answer(self, correct: bool, response_ms: int) -> None:
        self.pt.submit(correct)
        QTimer.singleShot(700, self._load_next)

    @guard("Placement._finish")
    def _finish(self) -> None:
        res = self.pt.save(
            self.ctx.db,
            apply_result=lambda d, t: self.ctx.curriculum.seed_from_placement(self.ctx.db, d, t),
        )
        self.ctx.settings.set("placement_done", True)
        self.test_area.hide()
        while self.results_layout.count():
            w = self.results_layout.takeAt(0).widget()
            if w:
                w.setParent(None)
        frame, lay = card("Your placement")
        for domain, info in res.items():
            row = QHBoxLayout()
            name = QLabel(f"<b>{domain.title()}</b>")
            lvl = QLabel(info["level"])
            lvl.setStyleSheet("color:#5b8def; font-weight:700;")
            row.addWidget(name)
            row.addStretch(1)
            row.addWidget(lvl)
            lay.addLayout(row)
        go = QPushButton("Start learning  \u2192")
        go.clicked.connect(lambda: self.navigate and self.navigate("session"))
        lay.addWidget(go)
        self.results_layout.addWidget(frame)
        self.results.show()
        self.pt = None
