"""Home dashboard: level overview, streak, progress, and quick actions."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout, QWidget,
)

from ...achievements import ACHIEVEMENTS, unlocked_titles
from ...adaptive import MasteryModel, level_for_rating
from ..celebration import animate_bar
from ..common import card, card_title, heading, subtle

DAILY_GOAL_XP = 50


class DashboardScreen(QWidget):
    def __init__(self, ctx, parent=None) -> None:
        super().__init__(parent)
        self.ctx = ctx
        self.navigate = None
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 20)
        root.setSpacing(16)

        self.greeting = heading("Welcome")
        # the profile name is user input - never let Qt auto-detect it as rich text
        self.greeting.setTextFormat(Qt.TextFormat.PlainText)
        root.addWidget(self.greeting)
        self.tagline = subtle("")
        root.addWidget(self.tagline)

        stats = QHBoxLayout()
        self.streak_card, sc = card("Streak")
        self.streak_val = QLabel("0 days")
        self.streak_val.setObjectName("StatValue")
        sc.addWidget(self.streak_val)
        self.xp_card, xc = card("Total XP")
        self.xp_val = QLabel("0")
        self.xp_val.setObjectName("StatValue")
        xc.addWidget(self.xp_val)
        self.acc_card, ac = card("Accuracy")
        self.acc_val = QLabel("-")
        self.acc_val.setObjectName("StatValue")
        ac.addWidget(self.acc_val)
        stats.addWidget(self.streak_card)
        stats.addWidget(self.xp_card)
        stats.addWidget(self.acc_card)
        root.addLayout(stats)

        goal_card, gc = card("Daily goal")
        self.goal_bar = QProgressBar()
        self.goal_bar.setMaximum(DAILY_GOAL_XP)
        self.goal_label = subtle("")
        gc.addWidget(self.goal_bar)
        gc.addWidget(self.goal_label)
        root.addWidget(goal_card)

        self.levels_card, self.levels_layout = card("Your levels")
        root.addWidget(self.levels_card)

        self.ach_card, self.ach_layout = card("Achievements")
        root.addWidget(self.ach_card)

        prog_card, pc = card("Curriculum progress")
        self.prog_bar = QProgressBar()
        self.prog_label = subtle("")
        pc.addWidget(self.prog_bar)
        pc.addWidget(self.prog_label)
        root.addWidget(prog_card)

        actions = QHBoxLayout()
        self.continue_btn = QPushButton("Continue learning  \u2192")
        self.continue_btn.clicked.connect(lambda: self.navigate and self.navigate("session"))
        self.review_btn = QPushButton("Review weak spots")
        self.review_btn.setObjectName("Secondary")
        self.review_btn.clicked.connect(lambda: self.navigate and self.navigate("review"))
        self.place_btn = QPushButton("Take placement test")
        self.place_btn.setObjectName("Secondary")
        self.place_btn.clicked.connect(lambda: self.navigate and self.navigate("placement"))
        actions.addWidget(self.continue_btn)
        actions.addWidget(self.review_btn)
        actions.addWidget(self.place_btn)
        actions.addStretch(1)
        root.addLayout(actions)
        root.addStretch(1)

    def on_show(self) -> None:
        prof = self.ctx.db.get_profile()
        name = prof.get("name", "Learner")
        self.greeting.setText(f"Welcome back, {name}")
        self.streak_val.setText(f"{prof.get('streak_days', 0)} days")
        self.xp_val.setText(str(prof.get("total_xp", 0)))
        n, c = self.ctx.db.attempt_counts()
        self.acc_val.setText(f"{int(100*c/n)}%" if n else "-")
        self.tagline.setText("Pick up where you left off, or jump into practice and dictation.")

        placement = self.ctx.db.latest_placement()
        self.place_btn.setText("Retake placement test" if placement else "Take placement test")

        today = self.ctx.db.today_xp()
        reduce = bool(self.ctx.settings.get("reduce_motion", False))
        animate_bar(self.goal_bar, min(DAILY_GOAL_XP, today), reduce_motion=reduce)
        if today >= DAILY_GOAL_XP:
            self.goal_label.setText(f"Daily goal reached - {today} XP today. Nice!")
        else:
            self.goal_label.setText(f"{today} / {DAILY_GOAL_XP} XP today")

        while self.ach_layout.count():
            w = self.ach_layout.takeAt(0).widget()
            if w:
                w.setParent(None)
        self.ach_layout.addWidget(card_title("Achievements"))
        titles = unlocked_titles(self.ctx.db)
        if titles:
            recent = "      ".join("\U0001F3C6  " + t for t in titles[-3:])
            lbl = QLabel(recent)
            lbl.setWordWrap(True)
            self.ach_layout.addWidget(lbl)
        else:
            self.ach_layout.addWidget(subtle("No achievements yet - complete a lesson to earn your first!"))
        gallery_btn = QPushButton(f"View all  ({len(titles)} / {len(ACHIEVEMENTS)})  →")
        gallery_btn.setObjectName("Secondary")
        gallery_btn.setAccessibleName("Open the achievements gallery")
        gallery_btn.clicked.connect(lambda: self.navigate and self.navigate("achievements"))
        self.ach_layout.addWidget(gallery_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        while self.levels_layout.count():
            item = self.levels_layout.takeAt(0)
            w = item.widget()
            if w and w is not self.levels_card:
                w.setParent(None)
        self.levels_layout.addWidget(card_title("Your levels"))
        row = QHBoxLayout()
        for domain in ("theory", "aural", "piano"):
            skills = [s.id for s in self.ctx.curriculum.by_domain(domain) if s.schedulable]
            rating = MasteryModel.overall_rating(self.ctx.db, skills)
            if domain in placement and self.ctx.db.attempt_counts()[0] == 0:
                level = placement[domain]["level"]
            else:
                level = level_for_rating(rating)
            lbl = QLabel(domain.title() + ":")
            val = QLabel(level)
            val.setObjectName("AccentValue")
            row.addWidget(lbl)
            row.addWidget(val)
            row.addSpacing(24)
        row.addStretch(1)
        holder = QWidget()
        holder.setLayout(row)
        self.levels_layout.addWidget(holder)

        summ = self.ctx.scheduler.progress_summary()
        self.prog_bar.setMaximum(summ["total"])
        animate_bar(self.prog_bar, summ["mastered"], reduce_motion=reduce)
        self.prog_label.setText(
            f"{summ['mastered']} of {summ['total']} skills mastered  \u00b7  "
            f"{summ['unlocked']} unlocked")
