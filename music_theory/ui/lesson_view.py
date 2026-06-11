"""Inline lesson viewer: pages of teaching content with optional audio
examples and staff illustrations, shown before a new skill is drilled."""

from __future__ import annotations

from typing import Callable, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ..curriculum.lessons import LessonPage
from ..errors import guard
from ..exercises.base import render_play
from ..theory.pitch import Note
from .widgets import StaffWidget


class LessonView(QWidget):
    def __init__(self, engine=None, parent=None) -> None:
        super().__init__(parent)
        self.engine = engine
        self.pages: list[LessonPage] = []
        self.page_idx = 0
        self._on_done: Optional[Callable] = None
        self._skill_title = ""

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        self.kicker = QLabel("")
        self.kicker.setStyleSheet("color:#5b8def; font-size:13px; font-weight:700;")
        root.addWidget(self.kicker)
        self.title = QLabel("")
        self.title.setWordWrap(True)
        self.title.setStyleSheet("font-size:22px; font-weight:800;")
        root.addWidget(self.title)
        self.body = QLabel("")
        self.body.setWordWrap(True)
        self.body.setTextFormat(Qt.TextFormat.RichText)
        self.body.setStyleSheet("font-size:16px; line-height:150%;")
        root.addWidget(self.body)

        self.staff = StaffWidget("treble")
        self.staff.hide()
        root.addWidget(self.staff)

        self.play_btn = QPushButton("▶  Listen")
        self.play_btn.clicked.connect(self._play)
        self.play_btn.hide()
        root.addWidget(self.play_btn, 0, Qt.AlignmentFlag.AlignLeft)

        root.addStretch(1)

        nav = QHBoxLayout()
        self.back_btn = QPushButton("← Back")
        self.back_btn.setObjectName("Secondary")
        self.back_btn.clicked.connect(self._back)
        self.progress = QLabel("")
        self.progress.setStyleSheet("color:#8b93a3;")
        self.next_btn = QPushButton("Continue →")
        self.next_btn.clicked.connect(self._next)
        nav.addWidget(self.back_btn)
        nav.addStretch(1)
        nav.addWidget(self.progress)
        nav.addStretch(1)
        nav.addWidget(self.next_btn)
        root.addLayout(nav)

    # -- API ----------------------------------------------------------------
    def set_lesson(self, skill_title: str, pages: list[LessonPage],
                   on_done: Callable = None) -> None:
        self._skill_title = skill_title
        self.pages = list(pages)
        self.page_idx = 0
        self._on_done = on_done
        self._render()

    # -- navigation -----------------------------------------------------------
    @guard("LessonView._next")
    def _next(self) -> None:
        if self.page_idx + 1 < len(self.pages):
            self.page_idx += 1
            self._render()
        elif self._on_done:
            self._on_done()

    @guard("LessonView._back")
    def _back(self) -> None:
        if self.page_idx > 0:
            self.page_idx -= 1
            self._render()

    @guard("LessonView._play")
    def _play(self) -> None:
        page = self.pages[self.page_idx] if self.pages else None
        if page is not None and page.play and self.engine:
            render_play(self.engine, page.play)

    # -- rendering --------------------------------------------------------------
    def _render(self) -> None:
        if not self.pages:
            return
        page = self.pages[self.page_idx]
        self.kicker.setText(f"NEW SKILL  ·  {self._skill_title}")
        self.title.setText(page.title)
        self.body.setText(page.body)
        self.play_btn.setVisible(bool(page.play))
        if page.staff:
            self.staff.show()
            self.staff.allow_input = False
            self.staff.set_clef(page.staff.get("clef", "treble"))
            self.staff.set_key_signature(page.staff.get("key_sig"))
            notes = page.staff.get("notes", "")
            if isinstance(notes, str):
                parsed = []
                for nm in notes.split():
                    try:
                        parsed.append(Note.parse(nm))
                    except (ValueError, KeyError):
                        pass
                self.staff.set_notes(parsed)
            else:
                self.staff.set_notes(list(notes))
        else:
            self.staff.hide()
        self.back_btn.setEnabled(self.page_idx > 0)
        last = self.page_idx == len(self.pages) - 1
        self.next_btn.setText("Start practicing →" if last else "Continue →")
        self.progress.setText(f"{self.page_idx + 1} / {len(self.pages)}")
        # auto-play examples so the concept is heard, not just read
        if page.play and self.engine:
            self._play()
