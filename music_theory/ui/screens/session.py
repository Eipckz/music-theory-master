"""Coursework session: the adaptive scheduler drives a stream of exercises
tuned to the learner's level, grouped into short lessons with a celebratory
summary so progress never dead-ends."""

from __future__ import annotations

import datetime

from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout, QWidget,
)

from ...adaptive import MasteryModel, level_for_rating
from ...curriculum.lessons import lesson_for
from ...errors import guard
from ...feedback_messages import pick_message
from ..common import card, heading, subtle
from ..exercise_player import ExercisePlayer
from ..lesson_view import LessonView
from .. import theme
from .dashboard import DAILY_GOAL_XP

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
        skill_row = QHBoxLayout()
        self.skill_label = subtle("")
        skill_row.addWidget(self.skill_label)
        self.lesson_btn = QPushButton("📖 Lesson")
        self.lesson_btn.setObjectName("Secondary")
        self.lesson_btn.setToolTip("Re-read the mini-lesson for this skill")
        self.lesson_btn.clicked.connect(self._review_lesson)
        self.lesson_btn.hide()
        skill_row.addWidget(self.lesson_btn)
        skill_row.addStretch(1)
        self.level_label = subtle("")
        skill_row.addWidget(self.level_label)
        root.addLayout(skill_row)
        self.lesson_bar = QProgressBar()
        self.lesson_bar.setMaximum(LESSON_LEN)
        self.lesson_bar.setValue(0)
        self.lesson_bar.setFormat("Lesson progress: %v / %m")
        root.addWidget(self.lesson_bar)

        self.player = ExercisePlayer(self.ctx.engine, self.ctx.midi,
                                     settings=self.ctx.settings)
        root.addWidget(self.player, 1)

        self.lesson = LessonView(self.ctx.engine)
        self.lesson.hide()
        root.addWidget(self.lesson, 1)

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
        self.lesson_skill_stats: dict[str, list[int]] = {}   # skill_id -> [n, correct]
        self._consec_correct = 0
        self._last_was_miss = False

    def preset_weak(self) -> None:
        """Start a lesson focused on the learner's weakest skills."""
        self._weak_mode = True
        self._reset_lesson()
        self.summary.hide()
        self.lesson.hide()
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
        self.lesson.hide()
        self.player.show()
        self.pick = self.ctx.scheduler.next_exercise(source="course", weak=self._weak_mode)
        if self.pick is None:
            self.skill_label.setText(
                "No skills available yet - take the placement test or visit Practice.")
            return
        skill = self.ctx.curriculum.get(self.pick.skill_id)
        title = skill.title if skill else self.pick.skill_id
        self.skill_label.setText(f"Skill: <b>{title}</b>  \u00b7  {self.pick.reason}")
        self.lesson_btn.setVisible(bool(lesson_for(self.pick.skill_id)))
        self._update_level_label(skill.domain if skill else self.pick.exercise.domain)
        if self._maybe_teach(skill):
            return
        self.player.set_exercise(
            self.pick.exercise, on_answer=self._on_answer, on_next=self._load_next,
            badge=f"{skill.level if skill else ''}  \u00b7  {self.pick.exercise.domain.title()}",
        )

    def _maybe_teach(self, skill) -> bool:
        """Show the skill's mini-lesson the first time it appears (Duolingo
        style: teach the concept, then drill it). Returns True if teaching."""
        if skill is None:
            return False
        if self.ctx.db.kv_get(f"taught.{skill.id}"):
            return False
        pages = lesson_for(skill.id)
        if not pages:
            return False
        self.player.hide()
        self.lesson.set_lesson(skill.title, pages, on_done=self._finish_teaching)
        self.lesson.show()
        return True

    @guard("Session._finish_teaching")
    def _finish_teaching(self) -> None:
        if self.pick is not None:
            self.ctx.db.kv_set(f"taught.{self.pick.skill_id}", True)
        self.lesson.hide()
        self.player.show()
        if self.pick is None:
            return
        skill = self.ctx.curriculum.get(self.pick.skill_id)
        self.player.set_exercise(
            self.pick.exercise, on_answer=self._on_answer, on_next=self._load_next,
            badge=f"{skill.level if skill else ''}  \u00b7  {self.pick.exercise.domain.title()}",
        )

    @guard("Session._review_lesson")
    def _review_lesson(self) -> None:
        """Re-open the current skill's lesson on demand."""
        if self.pick is None:
            return
        skill = self.ctx.curriculum.get(self.pick.skill_id)
        pages = lesson_for(self.pick.skill_id)
        if not skill or not pages:
            return
        self.player.hide()
        self.summary.hide()
        self.lesson.set_lesson(skill.title, pages, on_done=self._resume_after_review)
        self.lesson.show()

    @guard("Session._resume_after_review")
    def _resume_after_review(self) -> None:
        """Return to the in-progress exercise exactly as it was left."""
        self.lesson.hide()
        self.player.show()

    def _update_level_label(self, domain: str) -> None:
        ids = [s.id for s in self.ctx.curriculum.by_domain(domain) if s.schedulable]
        level = level_for_rating(MasteryModel.overall_rating(self.ctx.db, ids))
        self.level_label.setText(f"{domain.title()} level: <b>{level}</b>")

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
        stats = self.lesson_skill_stats.setdefault(self.pick.skill_id, [0, 0])
        stats[0] += 1
        stats[1] += 1 if correct else 0

        xp = 10 if correct else 2
        if correct and self.player.was_hinted:
            xp = 4
        goal_before = self.ctx.db.today_xp()
        self.ctx.db.add_xp(xp)
        self.lesson_xp += xp
        # surface the reward in the moment, not just on the dashboard
        self.player.feedback.setText(
            self.player.feedback.text() + f"   <b style='color:{theme.GOOD}'>+{xp} XP</b>")

        self._touch_streak()
        acc = int(100 * self.correct / self.answered) if self.answered else 0
        self.stat.setText(f"This session: {self.correct}/{self.answered} correct ({acc}%)")
        self.lesson_bar.setValue(min(LESSON_LEN, self.lesson_n))
        self._update_level_label(domain)

        after_level = level_for_rating(MasteryModel.overall_rating(self.ctx.db, domain_ids))
        after_mastered = self.ctx.curriculum.is_mastered(self.ctx.db, self.pick.skill_id)
        skill_title = skill.title if skill else self.pick.skill_id
        self._moment_messages(correct, domain=domain, level=after_level,
                              skill_title=skill_title)
        if after_mastered and not before_mastered:
            self._celebrate("mastery", skill_title,
                            pick_message(self.ctx.db, domain, after_level, "mastery",
                                         skill=skill_title, domain=domain.title()))
        elif after_level != before_level:
            self._celebrate("level_up", f"{domain.title()}: {after_level}",
                            pick_message(self.ctx.db, domain, after_level, "level_up",
                                         level=after_level, domain=domain.title()))
        if goal_before < DAILY_GOAL_XP <= self.ctx.db.today_xp():
            msg = pick_message(self.ctx.db, domain, after_level, "daily_goal",
                               domain=domain.title())
            win = self.window()
            # don't stack overlays: fall back to a toast if one is already up
            if hasattr(win, "celebrate") and not getattr(
                    getattr(win, "_celebration", None), "active", False):
                win.celebrate("Daily goal reached", msg, kind="daily_goal")
            else:
                self._notify(f"\u2705 Daily goal reached. {msg}", kind="success")

    def _moment_messages(self, correct: bool, *, domain: str, level: str,
                         skill_title: str) -> None:
        """Streak and comeback encouragement, appended under the feedback."""
        line = ""
        if correct:
            was_miss = self._last_was_miss
            self._consec_correct += 1
            self._last_was_miss = False
            if self._consec_correct >= 5 and self._consec_correct % 5 == 0:
                line = pick_message(self.ctx.db, domain, level, "correct_streak",
                                    streak=self._consec_correct, skill=skill_title,
                                    domain=domain.title())
            elif was_miss:
                line = pick_message(self.ctx.db, domain, level, "comeback_after_miss",
                                    skill=skill_title, domain=domain.title())
        else:
            self._consec_correct = 0
            self._last_was_miss = True
        if line:
            self.player.feedback.setText(
                self.player.feedback.text()
                + f"<br><span style='color:{theme.TEXT_MUTED}'>{line}</span>")

    def _celebrate(self, kind: str, title: str, message: str) -> None:
        win = self.window()
        if hasattr(win, "celebrate"):
            win.celebrate(title, message, kind=kind)
        else:  # headless tests drive the screen without a MainWindow
            self._notify(f"{title}. {message}", kind="success")

    def _show_summary(self) -> None:
        self.player.hide()
        self.lesson.hide()
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
        # encouragement from the no-repeat bank, tied to what was just drilled
        skill_id = next(iter(self.lesson_skills), "")
        skill = self.ctx.curriculum.get(skill_id)
        domain = skill.domain if skill else "theory"
        level = skill.level if skill else "Beginner"
        msg = pick_message(self.ctx.db, domain, level, "lesson_complete",
                           skill=(skill.title if skill else "this material"),
                           domain=domain.title())
        if msg:
            note = subtle(msg)
            note.setWordWrap(True)
            lay.addWidget(note)

        # per-session recap: what you worked on, and what to revisit
        if self.lesson_skill_stats:
            lines = []
            weakest, weakest_acc = None, 2.0
            for sid, (n, c) in self.lesson_skill_stats.items():
                sk = self.ctx.curriculum.get(sid)
                title = sk.title if sk else sid
                lines.append(f"{title}:  {c}/{n}")
                if n and c / n < weakest_acc:
                    weakest, weakest_acc = title, c / n
            recap = QLabel("<b>This lesson:</b><br>" + "<br>".join(lines))
            recap.setAccessibleName("Lesson recap by skill")
            lay.addWidget(recap)
            if weakest is not None and weakest_acc < 1.0:
                lay.addWidget(subtle(f"Worth another look: {weakest}. "
                                     "It will come back in your reviews."))
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
        if last == yesterday:
            streak += 1
        else:
            # streak broken: remember it so rebuilding one earns "Comeback"
            if streak >= 3 and last:
                self.ctx.db.kv_set("streak.lost_after_3", True)
            streak = 1
        self.ctx.db.update_profile(last_active_day=today, streak_days=streak)
