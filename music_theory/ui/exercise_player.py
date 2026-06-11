"""Reusable exercise player: renders any Exercise, collects the answer through
the appropriate input control, grades it, and shows feedback."""

from __future__ import annotations

import time
from typing import Callable, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QButtonGroup, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QWidget,
)

from ..errors import guard
from ..exercises.base import Exercise, InputMode, render_play
from ..exercises.teaching import concept_for, hint_for
from ..theory.pitch import Note
from .theme import ACCENT, BAD, GOOD
from .widgets import PianoWidget, StaffWidget

_DUR_LABELS = [("\U0001D15D 4", 4.0), ("\U0001D15E 2", 2.0), ("\u2669 1", 1.0),
               ("\u266a \u00bd", 0.5), ("\u266b \u00bc", 0.25), ("\u2669. 1.5", 1.5)]


class ExercisePlayer(QWidget):
    def __init__(self, engine=None, midi=None, parent=None) -> None:
        super().__init__(parent)
        self.engine = engine
        self.midi = midi
        self.ex: Optional[Exercise] = None
        self._on_answer: Optional[Callable] = None
        self._on_next: Optional[Callable] = None
        self._entry: list[int] = []
        self._seq: list[str] = []
        self._rhythm: list[float] = []
        self._answered = False
        self._show_next = True
        self._t0 = 0.0
        self._hint_text = ""
        self.was_hinted = False
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(24, 20, 24, 20)
        self._root.setSpacing(14)
        self._build_static()
        self._install_shortcuts()

    def _install_shortcuts(self) -> None:
        ctx = Qt.ShortcutContext.WidgetWithChildrenShortcut
        for i in range(1, 10):
            sc = QShortcut(QKeySequence(str(i)), self)
            sc.setContext(ctx)
            sc.activated.connect(lambda n=i: self._choose_index(n - 1))
        replay = QShortcut(QKeySequence("R"), self)
        replay.setContext(ctx)
        replay.activated.connect(self._play)
        for key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            sc = QShortcut(QKeySequence(key), self)
            sc.setContext(ctx)
            sc.activated.connect(self._enter_key)

    def _build_static(self) -> None:
        self.badge = QLabel("")
        self.badge.setStyleSheet("color:#8b93a3; font-size:12px; font-weight:600;")
        self.prompt = QLabel("")
        self.prompt.setWordWrap(True)
        self.prompt.setStyleSheet("font-size:19px; font-weight:600;")
        self.staff = StaffWidget("treble")
        self.audio_row = QWidget()
        self.audio_layout = QHBoxLayout(self.audio_row)
        self.audio_layout.setContentsMargins(0, 0, 0, 0)
        self.input_host = QWidget()
        self.input_layout = QVBoxLayout(self.input_host)
        self.input_layout.setContentsMargins(0, 0, 0, 0)
        self.hint_row = QWidget()
        hint_layout = QHBoxLayout(self.hint_row)
        hint_layout.setContentsMargins(0, 0, 0, 0)
        self.hint_btn = QPushButton("\U0001F4A1 Hint")
        self.hint_btn.setObjectName("Secondary")
        self.hint_btn.clicked.connect(self._show_hint)
        hint_layout.addWidget(self.hint_btn)
        self.hint_label = QLabel("")
        self.hint_label.setWordWrap(True)
        self.hint_label.setStyleSheet("color:#c9a14a; font-size:14px;")
        hint_layout.addWidget(self.hint_label, 1)
        self.hint_row.hide()
        self.feedback = QLabel("")
        self.feedback.setWordWrap(True)
        self.feedback.setStyleSheet("font-size:15px;")
        self.feedback.setTextFormat(Qt.TextFormat.RichText)
        self.next_btn = QPushButton("Next  \u2192")
        self.next_btn.clicked.connect(self._next)
        self.next_btn.hide()
        for w in (self.badge, self.prompt, self.staff, self.audio_row, self.input_host,
                  self.hint_row, self.feedback, self.next_btn):
            self._root.addWidget(w)
        self._root.addStretch(1)

    # -- load --------------------------------------------------------------
    def set_exercise(self, ex: Exercise, *, on_answer: Callable = None,
                     on_next: Callable = None, badge: str = "",
                     show_next: bool = True) -> None:
        self.ex = ex
        self._on_answer = on_answer
        self._on_next = on_next
        self._show_next = show_next
        self._entry, self._seq, self._rhythm = [], [], []
        self._answered = False
        self._t0 = time.time()
        self.badge.setText(badge or f"{ex.domain.title()}  \u00b7  difficulty {ex.difficulty:.1f}")
        self.prompt.setText(ex.prompt)
        self.feedback.setText("")
        self.next_btn.hide()
        self.was_hinted = False
        self._hint_text = ex.hint or hint_for(ex.etype)
        self.hint_label.setText("")
        self.hint_btn.setVisible(bool(self._hint_text))
        self.hint_row.setVisible(bool(self._hint_text))
        self._setup_staff_prompt()
        self._setup_audio()
        self._clear_layout(self.input_layout)
        self._build_input()
        self.setFocus()

    def _show_hint(self) -> None:
        if self._answered or not self._hint_text:
            return
        self.was_hinted = True
        self.hint_label.setText(self._hint_text)
        self.hint_btn.hide()

    def _setup_staff_prompt(self) -> None:
        sp = self.ex.tags.get("staff_prompt")
        if sp:
            self.staff.show()
            self.staff.allow_input = False
            self.staff.set_clef(sp.get("clef", "treble"))
            self.staff.set_key_signature(sp.get("key_sig"))
            self.staff.set_notes(sp.get("notes", []))
        else:
            self.staff.hide()

    def _setup_audio(self) -> None:
        self._clear_layout(self.audio_layout)
        if self.ex.play:
            label = "\u25b6  Play" if self.ex.domain == "aural" else "\u25b6  Listen"
            btn = QPushButton(label)
            btn.clicked.connect(self._play)
            self.audio_layout.addWidget(btn)
            replay = QPushButton("\u21BB Replay")
            replay.setObjectName("Secondary")
            replay.clicked.connect(self._play)
            self.audio_layout.addWidget(replay)
            self.audio_layout.addStretch(1)
            self.audio_row.show()
            if self.ex.domain == "aural":
                self._play()
        else:
            self.audio_row.hide()

    @guard("ExercisePlayer._play")
    def _play(self) -> None:
        if self.engine and self.ex and self.ex.play:
            render_play(self.engine, self.ex.play)

    # -- input builders ----------------------------------------------------
    def _build_input(self) -> None:
        mode = self.ex.input_mode
        if mode == InputMode.MULTIPLE_CHOICE:
            self._build_choices()
        elif mode == InputMode.TEXT:
            self._build_text()
        elif mode in (InputMode.NOTE_ENTRY,):
            self._build_note_entry()
        elif mode == InputMode.PIANO:
            self._build_piano()
        elif mode == InputMode.RHYTHM:
            self._build_rhythm()
        elif mode == InputMode.SEQUENCE:
            self._build_sequence()

    def _build_choices(self) -> None:
        self._choice_btns = []
        for choice in self.ex.choices:
            b = QPushButton(choice)
            b.setObjectName("Choice")
            b.clicked.connect(lambda _=False, c=choice: self._grade(c))
            self.input_layout.addWidget(b)
            self._choice_btns.append(b)

    def _build_text(self) -> None:
        self.text_edit = QLineEdit()
        self.text_edit.setPlaceholderText("Type your answer and press Enter")
        self.text_edit.returnPressed.connect(lambda: self._grade(self.text_edit.text()))
        self.input_layout.addWidget(self.text_edit)
        submit = QPushButton("Submit")
        submit.clicked.connect(lambda: self._grade(self.text_edit.text()))
        self.input_layout.addWidget(submit)

    def _build_note_entry(self) -> None:
        given = self.ex.tags.get("given_first")
        if given is not None:
            self._entry = [int(given)]
        self.entry_label = QLabel()
        self.input_layout.addWidget(self.entry_label)
        self.entry_piano = PianoWidget(48, 84)
        self.entry_piano.notePressed.connect(self._add_entry_note)
        self.input_layout.addWidget(self.entry_piano)
        row = QHBoxLayout()
        back = QPushButton("\u232B Backspace"); back.setObjectName("Secondary")
        back.clicked.connect(self._backspace_entry)
        clear = QPushButton("Clear"); clear.setObjectName("Secondary")
        clear.clicked.connect(self._clear_entry)
        submit = QPushButton("Submit")
        submit.clicked.connect(lambda: self._grade(list(self._entry)))
        row.addWidget(back); row.addWidget(clear); row.addStretch(1); row.addWidget(submit)
        self.input_layout.addLayout(row)
        self._refresh_entry()

    def _build_piano(self) -> None:
        self.entry_label = QLabel()
        self.input_layout.addWidget(self.entry_label)
        self.entry_piano = PianoWidget(48, 84)
        self.entry_piano.notePressed.connect(self._add_entry_note)
        self.input_layout.addWidget(self.entry_piano)
        if self.midi is not None:
            try:
                self.midi.noteOn.connect(self._midi_note)
            except Exception:  # noqa: BLE001
                pass
        row = QHBoxLayout()
        clear = QPushButton("Clear"); clear.setObjectName("Secondary")
        clear.clicked.connect(self._clear_entry)
        submit = QPushButton("Submit")
        submit.clicked.connect(lambda: self._grade(list(self._entry)))
        row.addWidget(clear); row.addStretch(1); row.addWidget(submit)
        self.input_layout.addLayout(row)
        self._refresh_entry()

    def _build_rhythm(self) -> None:
        self.entry_label = QLabel()
        self.input_layout.addWidget(self.entry_label)
        grid = QHBoxLayout()
        for label, val in _DUR_LABELS:
            b = QPushButton(label); b.setObjectName("Choice")
            b.clicked.connect(lambda _=False, v=val: self._add_rhythm(v))
            grid.addWidget(b)
        self.input_layout.addLayout(grid)
        row = QHBoxLayout()
        back = QPushButton("\u232B"); back.setObjectName("Secondary")
        back.clicked.connect(self._backspace_rhythm)
        submit = QPushButton("Submit")
        submit.clicked.connect(lambda: self._grade(list(self._rhythm)))
        row.addWidget(back); row.addStretch(1); row.addWidget(submit)
        self.input_layout.addLayout(row)
        self._refresh_rhythm()

    def _build_sequence(self) -> None:
        self.entry_label = QLabel()
        self.input_layout.addWidget(self.entry_label)
        grid = QHBoxLayout()
        grid.setSpacing(6)
        for label in self.ex.choices:
            b = QPushButton(label); b.setObjectName("Choice")
            b.clicked.connect(lambda _=False, c=label: self._add_seq(c))
            grid.addWidget(b)
        self.input_layout.addLayout(grid)
        row = QHBoxLayout()
        back = QPushButton("\u232B"); back.setObjectName("Secondary")
        back.clicked.connect(self._backspace_seq)
        submit = QPushButton("Submit")
        submit.clicked.connect(lambda: self._grade(list(self._seq)))
        row.addWidget(back); row.addStretch(1); row.addWidget(submit)
        self.input_layout.addLayout(row)
        self._refresh_seq()

    # -- entry helpers -----------------------------------------------------
    def _add_entry_note(self, midi: int) -> None:
        if self._answered:
            return
        self._entry.append(int(midi))
        if self.engine:
            self.engine.play_note(int(midi), dur=0.6)
        self._refresh_entry()

    def _midi_note(self, midi: int, _vel: int) -> None:
        self._add_entry_note(midi)

    def _backspace_entry(self) -> None:
        if self._entry:
            self._entry.pop()
            self._refresh_entry()

    def _clear_entry(self) -> None:
        given = self.ex.tags.get("given_first")
        self._entry = [int(given)] if given is not None and self.ex.input_mode == InputMode.NOTE_ENTRY else []
        self._refresh_entry()

    def _refresh_entry(self) -> None:
        notes = [Note.from_midi(m) for m in self._entry]
        self.entry_label.setText("Your entry:  " + " ".join(n.name for n in notes) if notes
                                 else "Your entry:  (play/click notes)")
        if self.ex.tags.get("staff_prompt") is not None and self.ex.input_mode == InputMode.NOTE_ENTRY:
            self.staff.show()
            self.staff.set_notes(notes)
        if hasattr(self, "entry_piano"):
            self.entry_piano.clear_highlight()
            self.entry_piano.highlight(self._entry, ACCENT)

    def _add_rhythm(self, val: float) -> None:
        if not self._answered:
            self._rhythm.append(val)
            self._refresh_rhythm()

    def _backspace_rhythm(self) -> None:
        if self._rhythm:
            self._rhythm.pop()
            self._refresh_rhythm()

    def _refresh_rhythm(self) -> None:
        total = sum(self._rhythm)
        self.entry_label.setText(f"Rhythm:  {', '.join(str(v) for v in self._rhythm) or '(empty)'}   "
                                 f"[{total:g}/{self.ex.tags.get('beats', 4)} beats]")

    def _add_seq(self, label: str) -> None:
        if not self._answered:
            self._seq.append(label)
            self._refresh_seq()

    def _backspace_seq(self) -> None:
        if self._seq:
            self._seq.pop()
            self._refresh_seq()

    def _refresh_seq(self) -> None:
        self.entry_label.setText("Sequence:  " + (" - ".join(self._seq) or "(empty)"))

    # -- grading / feedback ------------------------------------------------
    @guard("ExercisePlayer._grade")
    def _grade(self, response) -> None:
        if self._answered or self.ex is None:
            return
        self._answered = True
        self.hint_btn.hide()
        correct = self.ex.grade(response)
        elapsed_ms = int((time.time() - self._t0) * 1000)
        self._show_feedback(correct)
        if self._on_answer:
            self._on_answer(correct, elapsed_ms)

    def _answer_text(self) -> str:
        if self.ex.input_mode in (InputMode.MULTIPLE_CHOICE, InputMode.TEXT):
            ans = self.ex.answer
            if isinstance(ans, (list, tuple, set)):
                return ", ".join(str(x) for x in ans)
            return str(ans)
        return ""  # note/sequence/rhythm answers are spelled out in explanation

    def _show_feedback(self, correct: bool) -> None:
        color = GOOD if correct else BAD
        if correct:
            self.feedback.setText(
                f"<b style='color:{color}'>Correct!</b>  {self.ex.explanation}")
        else:
            parts = []
            ans = self._answer_text()
            if ans:
                parts.append(f"The answer was <b>{ans}</b>.")
            if self.ex.explanation:
                parts.append(self.ex.explanation)
            teach = self.ex.teach or concept_for(self.ex.etype)
            body = " ".join(parts)
            if teach:
                body += (f"<br><span style='color:#9aa3b2; font-size:14px;'>{teach}</span>")
            self.feedback.setText(f"<b style='color:{color}'>Not quite.</b>  {body}")
        # reveal
        rev = self.ex.reveal or {}
        if "staff" in rev:
            self.staff.show()
            self.staff.set_clef(rev["staff"].get("clef", "treble"))
            self.staff.set_key_signature(rev["staff"].get("key_sig"))
            entered = [Note.from_midi(m) for m in self._entry] if self._entry else []
            self.staff.set_notes(entered, ghost=rev["staff"].get("notes", []))
        if "highlight" in rev and hasattr(self, "entry_piano"):
            self.entry_piano.flash(rev["highlight"], GOOD if correct else "#c98a3a")
        if hasattr(self, "_choice_btns"):
            for b in self._choice_btns:
                b.setEnabled(False)
                if b.text() == str(self.ex.answer):
                    b.setStyleSheet(f"background:{GOOD}; color:white;")
        if self._show_next:
            self.next_btn.show()
            self.next_btn.setFocus()

    @guard("ExercisePlayer._next")
    def _next(self) -> None:
        if self._on_next:
            self._on_next()

    # -- keyboard shortcuts ------------------------------------------------
    def _choose_index(self, idx: int) -> None:
        if self._answered or self.ex is None:
            return
        if self.ex.input_mode == InputMode.MULTIPLE_CHOICE and \
                hasattr(self, "_choice_btns") and 0 <= idx < len(self._choice_btns):
            self._choice_btns[idx].click()

    def _enter_key(self) -> None:
        if self.next_btn.isVisible():
            self._next()
        elif not self._answered:
            self._submit_current()

    def _submit_current(self) -> None:
        if self.ex is None:
            return
        mode = self.ex.input_mode
        if mode == InputMode.TEXT and hasattr(self, "text_edit"):
            self._grade(self.text_edit.text())
        elif mode in (InputMode.NOTE_ENTRY, InputMode.PIANO):
            self._grade(list(self._entry))
        elif mode == InputMode.RHYTHM:
            self._grade(list(self._rhythm))
        elif mode == InputMode.SEQUENCE:
            self._grade(list(self._seq))

    # -- util --------------------------------------------------------------
    def _clear_layout(self, layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
            else:
                sub = item.layout()
                if sub is not None:
                    self._clear_sublayout(sub)

    def _clear_sublayout(self, layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
            elif item.layout() is not None:
                self._clear_sublayout(item.layout())
