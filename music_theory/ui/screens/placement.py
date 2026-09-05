"""Adaptive placement test screen: estimates the learner's level per domain,
then seeds the curriculum so coursework starts at the right difficulty."""

from __future__ import annotations

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout, QWidget, QCheckBox, QScrollArea,
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
        self.player = ExercisePlayer(self.ctx.engine, self.ctx.midi,
                                     settings=self.ctx.settings)
        ta.addWidget(self.player, 1)
        actions = QHBoxLayout()
        self.unknown = QPushButton("I don't know yet")
        self.unknown.clicked.connect(lambda: self._on_answer(False, 0))
        actions.addWidget(self.unknown)
        cancel = QPushButton("Cancel without saving")
        cancel.clicked.connect(self._reset_to_intro)
        actions.addWidget(cancel)
        ta.addLayout(actions)
        self.test_area.hide()
        root.addWidget(self.test_area, 1)

        self.results = QWidget()
        self.results_layout = QVBoxLayout(self.results)
        self.results_layout.setContentsMargins(0, 0, 0, 0)
        self.results.hide()
        self.result_scroll = QScrollArea()
        self.result_scroll.setWidgetResizable(True)
        self.result_scroll.setWidget(self.results)
        self.result_scroll.hide()
        root.addWidget(self.result_scroll, 1)
        root.addStretch(0)
        self._reset_to_intro()

    def _build_intro(self) -> QWidget:
        frame, lay = card("How it works")
        lay.addWidget(subtle(
            "Estimate a starting point in written theory, listening and keyboard skills. "
            "Adaptive questions find a working difficulty; confirmation and breadth checks "
            "look for gaps, including rhythm and collegiate tonal topics. This is a provisional "
            "practice recommendation, not a comprehensive certification of your musicianship. "
            "Use 'I don't know yet' instead of guessing. Keyboard questions accept the on-screen piano; "
            "no MIDI device is required. Retakes preserve your earned course progress."))
        self.comprehensive = QCheckBox("Include breadth checks (recommended; up to 58 questions across all domains)")
        self.comprehensive.setChecked(True)
        lay.addWidget(self.comprehensive)
        domains = QHBoxLayout()
        self.domain_checks = {}
        for domain in ("theory", "aural", "piano"):
            check = QCheckBox(domain.title())
            check.setChecked(True)
            self.domain_checks[domain] = check
            domains.addWidget(check)
        audio = QPushButton("Check sound")
        audio.clicked.connect(self._check_sound)
        domains.addWidget(audio)
        lay.addLayout(domains)
        row = QHBoxLayout()
        self.start_btn = QPushButton("Start placement")
        self.start_btn.clicked.connect(self._start)
        row.addWidget(self.start_btn)
        self.skip_btn = QPushButton("Skip — start from the beginning")
        self.skip_btn.setObjectName("Secondary")
        self.skip_btn.setToolTip("No test: begin the course at the first skills. "
                                 "You can take the placement test any time.")
        self.skip_btn.clicked.connect(self._skip)
        row.addWidget(self.skip_btn)
        row.addStretch(1)
        lay.addLayout(row)
        return frame

    @guard("Placement.sound")
    def _check_sound(self):
        self.ctx.engine.play_melody([60, 64, 67])

    @guard("Placement._skip")
    def _skip(self) -> None:
        """Beginners shouldn't be forced through a multi-domain test: start
        the course at the very beginning (never an overestimate)."""
        self.ctx.settings.set("placement_done", True)
        if self.navigate:
            self.navigate("session")

    def _reset_to_intro(self) -> None:
        """Restore the intro/start view so the test can always be (re)started."""
        self.pt = None
        prior = self.ctx.db.latest_placement()
        self.start_btn.setText("Retake placement test" if prior else "Start placement")
        self.test_area.hide()
        self.results.hide()
        self.result_scroll.hide()
        self.ctx.engine.stop()
        self.intro.show()

    def on_show(self) -> None:
        if self.pt is None:
            self._reset_to_intro()

    @guard("Placement._start")
    def _start(self) -> None:
        domains = [d for d, check in self.domain_checks.items() if check.isChecked()]
        if not domains:
            self.start_btn.setText("Select at least one domain above")
            return
        self.pt = PlacementTest(domains=domains, max_items=12, comprehensive=self.comprehensive.isChecked())
        self.intro.hide()
        self.results.hide()
        self.result_scroll.hide()
        self.test_area.show()
        self._load_next()

    @guard("Placement._load_next")
    def _load_next(self) -> None:
        if self.pt is None:
            return
        ex = self.pt.next_item()
        done, total = self.pt.progress
        self.progress.setMaximum(total)
        self.progress.setValue(done)
        if ex is None:
            self._finish()
            return
        dom = self.pt.current_domain
        phase = self.pt.state[dom].phase
        self.domain_label.setText(
            f"Question {done + 1} of at most {total}  ·  {dom.title()} · {phase.title()}")
        self.unknown.setEnabled(True)
        self.player.setEnabled(True)
        # show_feedback=False: during assessment we acknowledge the answer
        # without revealing right/wrong, so nothing must be read against a
        # timer and the staircase isn't telegraphed
        self.player.set_exercise(ex, on_answer=self._on_answer, show_next=False,
                                 show_feedback=False)

    @guard("Placement._on_answer")
    def _on_answer(self, correct: bool, response_ms: int) -> None:
        if self.pt is None or self.pt._current is None:
            return
        self.pt.submit(correct)
        self.unknown.setEnabled(False)
        self.player.setEnabled(False)
        active = self.pt
        QTimer.singleShot(700, lambda: self._load_next() if self.pt is active else None)

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
        frame, lay = card("Your provisional starting point")
        for domain, info in res.items():
            row = QHBoxLayout()
            name = QLabel(f"<b>{domain.title()}</b>")
            lvl = QLabel(info["level"])
            lvl.setObjectName("AccentValue")
            row.addWidget(name)
            row.addStretch(1)
            row.addWidget(lvl)
            lay.addLayout(row)
            detail = QLabel(f"{info['items']} questions across {info['topics']} exercise types. "
                            + ("Review: " + "; ".join(info["review"]) if info["review"] else "No misses in this sample; continue lessons to confirm mastery."))
            detail.setWordWrap(True)
            lay.addWidget(detail)
        omitted = set(self.domain_checks) - set(res)
        if omitted:
            lay.addWidget(QLabel("Not assessed: " + ", ".join(sorted(omitted))))
        go = QPushButton("Start learning  \u2192")
        go.clicked.connect(lambda: self.navigate and self.navigate("session"))
        lay.addWidget(go)
        self.results_layout.addWidget(frame)
        self.results.show()
        self.result_scroll.show()
        self.pt = None
