"""Coursework session: the adaptive scheduler drives a stream of exercises
tuned to the learner's level, grouped into short lessons with a celebratory
summary so progress never dead-ends."""

from __future__ import annotations

import datetime

from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout, QWidget,
)

from ...adaptive import MasteryModel, level_for_rating
from ...errors import guard
from ..common import card, heading, subtle
from ..exercise_player import ExercisePlayer

LESSON_LEN = 10


class SessionScreen(QWidget):
    def __init__(self, ctx, parent=None) -> None:
        super().__init__(parent)
        self.ctx = ctx
        self.navigate = None
        self.pick = None
        self.answered = 0
        self.correct = 0
        self._weak_mode = False
        self._reset_lesson()

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 16)
        header = QHBoxLayout()
        self.title = heading("Your Course")
        header.addWidget(self.title)
        header.addStretch(1)
        self.stat = subtle("")
        header.addWidget(self.stat)
        root.addLayout(header)
        self.skill_label = subtle("")
        root.addWidget(self.skill_label)
        self.lesson_bar = QProgressBar()
        self.lesson_bar.setMaximum(LESSON_LEN)
        self.lesson_bar.setValue(0)
        self.lesson_bar.setFormat("Lesson progress: %v / %m")
        root.addWidget(self.lesson_bar)

        self.player = ExercisePlayer(self.ctx.engine, self.ctx.midi)
        root.addWidget(self.player, 1)

        self.summary = QWidget()
        self.summary_layout = QVBoxLayout(self.summary)
        self.summary_layout.setContentsMargins(0, 0, 0, 0)
        self.summary.hide()
        root.addWidget(self.summary, 1)

    def _reset_lesson(self) -> None:
        self.lesson_n = 0
        self.lesson_correct = 0
        self.lesson_xp = 0
        self.lesson_skills: set[str] = set()

    def preset_weak(self) -> None:
        """Start a lesson focused on the learner's weakest skills."""
        self._weak_mode = True
        self._reset_lesson()
        self.summary.hide()
        self.player.show()
        self._load_next()

    def on_show(self) -> None:
        if self.pick is None and self.summary.isHidden():
            self._load_next()

    @guard("Session._load_next")
    def _load_next(self) -> None:
        if self.lesson_n >= LESSON_LEN:
            self._show_summary()
            return
        self.summary.hide()
        self.player.show()
        self.pick = self.ctx.scheduler.next_exercise(source="course", weak=self._weak_mode)
        if self.pick is None:
            self.skill_label.setText(
                "No skills available yet - take the placement test or visit Practice.")
            return
        skill = self.ctx.curriculum.get(self.pick.skill_id)
        title = skill.title if skill else self.pick.skill_id
        self.skill_label.setText(f"Skill: <b>{title}</b>  \u00b7  {self.pick.reason}")
        self.player.set_exercise(
            self.pick.exercise, on_answer=self._on_answer, on_next=self._load_next,
            badge=f"{skill.level if skill else ''}  \u00b7  {self.pick.exercise.domain.title()}",
        )

    @guard("Session._on_answer")
    def _on_answer(self, correct: bool, response_ms: int) -> None:
        if self.pick is None:
            return
        skill = self.ctx.curriculum.get(self.pick.skill_id)
        domain = skill.domain if skill else self.pick.exercise.domain
        domain_ids = [s.id for s in self.ctx.curriculum.by_domain(domain) if s.schedulable]
        before_level = level_for_rating(MasteryModel.overall_rating(self.ctx.db, domain_ids))
        before_mastered = self.ctx.curriculum.is_mastered(self.ctx.db, self.pick.skill_id)

        self.ctx.scheduler.record(
            self.pick.skill_id, correct, difficulty=self.pick.difficulty,
            domain=domain, etype=self.pick.etype, response_ms=response_ms, source="course",
        )
        self.answered += 1
        self.correct += 1 if correct else 0
        self.lesson_n += 1
        self.lesson_correct += 1 if correct else 0
        self.lesson_skills.add(self.pick.skill_id)

        xp = 10 if correct else 2
        if correct and self.player.was_hinted:
            xp = 4
        self.ctx.db.add_xp(xp)
        self.lesson_xp += xp

        self._touch_streak()
        acc = int(100 * self.correct / self.answered) if self.answered else 0
        self.stat.setText(f"This session: {self.correct}/{self.answered} correct ({acc}%)")
        self.lesson_bar.setValue(min(LESSON_LEN, self.lesson_n))

        after_level = level_for_rating(MasteryModel.overall_rating(self.ctx.db, domain_ids))
        after_mastered = self.ctx.curriculum.is_mastered(self.ctx.db, self.pick.skill_id)
        if after_mastered and not before_mastered:
            self._notify(f"\u2b50 Skill mastered: {skill.title if skill else ''}!", kind="success")
        elif after_level != before_level:
            self._notify(f"\U0001F389 Level up! {domain.title()} is now {after_level}.", kind="success")

    def _show_summary(self) -> None:
        self.player.hide()
        while self.summary_layout.count():
            w = self.summary_layout.takeAt(0).widget()
            if w:
                w.setParent(None)
        acc = int(100 * self.lesson_correct / self.lesson_n) if self.lesson_n else 0
        frame, lay = card("Lesson complete  \U0001F3B5")
        score = QLabel(f"<span style='font-size:22px; font-weight:800;'>"
                       f"{self.lesson_correct}/{self.lesson_n}</span>  correct  ({acc}%)")
        lay.addWidget(score)
        lay.addWidget(QLabel(f"+{self.lesson_xp} XP earned this lesson"))
        prof = self.ctx.db.get_profile()
        lay.addWidget(subtle(f"Streak: {prof.get('streak_days', 0)} days   \u00b7   "
                             f"Total XP: {prof.get('total_xp', 0)}"))
        lay.addWidget(subtle("Outstanding!" if acc >= 90 else
                             "Nice work - you're getting it." if acc >= 60 else
                             "Keep going - every rep builds the skill."))
        self._unlock_lesson_achievements(acc)

        row = QHBoxLayout()
        cont = QPushButton("Continue  \u2192")
        cont.clicked.connect(self._continue)
        home = QPushButton("Back to Home")
        home.setObjectName("Secondary")
        home.clicked.connect(lambda: self.navigate and self.navigate("dashboard"))
        row.addWidget(cont)
        row.addWidget(home)
        row.addStretch(1)
        lay.addLayout(row)
        self.summary_layout.addWidget(frame)
        self.summary_layout.addStretch(1)
        self.summary.show()

    @guard("Session._continue")
    def _continue(self) -> None:
        self._weak_mode = False
        self._reset_lesson()
        self.lesson_bar.setValue(0)
        self.summary.hide()
        self.player.show()
        self._load_next()

    def _unlock_lesson_achievements(self, accuracy: int) -> None:
        from ...achievements import evaluate_lesson
        for title in evaluate_lesson(self.ctx.db, accuracy=accuracy, lesson_len=self.lesson_n):
            self._notify(f"\U0001F3C6 Achievement unlocked: {title}", kind="success")

    def _notify(self, message: str, *, kind: str = "info") -> None:
        win = self.window()
        if hasattr(win, "toast"):
            win.toast(message, kind=kind)

    def _touch_streak(self) -> None:
        today = datetime.date.today().isoformat()
        prof = self.ctx.db.get_profile()
        last = prof.get("last_active_day", "")
        if last == today:
            return
        streak = prof.get("streak_days", 0)
        yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
        streak = streak + 1 if last == yesterday else 1
        self.ctx.db.update_profile(last_active_day=today, streak_days=streak)
