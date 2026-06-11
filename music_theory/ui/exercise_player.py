"""Reusable exercise player: renders any Exercise, collects the answer through
the appropriate input control, grades it, and shows feedback."""

from __future__ import annotations

import time
from typing import Callable, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication, QButtonGroup, QComboBox, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QVBoxLayout, QWidget,
)

from ..errors import guard
from ..exercises.base import Exercise, InputMode, render_play
from ..exercises.teaching import concept_for, hint_for
from ..theory.pitch import Note
from .theme import ACCENT, BAD, GOOD, TEXT_MUTED, WARN
from .widgets import PianoWidget, StaffWidget

_DUR_LABELS = [("\U0001D15D 4", 4.0), ("\U0001D15E 2", 2.0), ("\u2669 1", 1.0),
               ("\u266a \u00bd", 0.5), ("\u266b \u00bc", 0.25), ("\u2669. 1.5", 1.5)]
_DUR_GLYPHS = {4.0: "\U0001D15D", 2.0: "\U0001D15E", 1.0: "\u2669",
               0.5: "\u266a", 0.25: "\u266b", 1.5: "\u2669."}
_DUR_NAMES = {4.0: "Whole note, 4 beats", 2.0: "Half note, 2 beats",
              1.0: "Quarter note, 1 beat", 0.5: "Eighth note, half a beat",
              0.25: "Sixteenth note, quarter beat", 1.5: "Dotted quarter, 1.5 beats"}
_SPEED_OPTIONS = (("0.5\u00d7 speed", 0.5), ("0.75\u00d7 speed", 0.75),
                  ("1\u00d7 speed", 1.0), ("1.25\u00d7 speed", 1.25))


class ExercisePlayer(QWidget):
    def __init__(self, engine=None, midi=None, parent=None, settings=None) -> None:
        super().__init__(parent)
        self.engine = engine
        self.midi = midi
        # Playback-speed factor: lets learners slow dictation down. Seeded
        # from the "default_tempo" setting (90 bpm = 1x), adjustable per
        # session via the speed selector next to the Play button.
        self._tempo_factor = 1.0
        if settings is not None:
            try:
                self._tempo_factor = max(0.4, min(1.5, float(settings.get("default_tempo", 90)) / 90.0))
            except Exception:  # noqa: BLE001 - settings must never break the player
                self._tempo_factor = 1.0
        self.ex: Optional[Exercise] = None
        self._on_answer: Optional[Callable] = None
        self._on_next: Optional[Callable] = None
        self._entry: list[int] = []
        self._seq: list[str] = []
        self._rhythm: list[float] = []
        self._voices: list[list[int]] = []
        self._voice_idx = 0
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
        back = QShortcut(QKeySequence(Qt.Key.Key_Backspace), self)
        back.setContext(ctx)
        back.activated.connect(self._backspace_current)
        for key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            sc = QShortcut(QKeySequence(key), self)
            sc.setContext(ctx)
            sc.activated.connect(self._enter_key)

    def _build_static(self) -> None:
        self.badge = QLabel("")
        self.badge.setObjectName("Badge")
        self.prompt = QLabel("")
        self.prompt.setWordWrap(True)
        self.prompt.setObjectName("Prompt")
        self.prompt.setAccessibleName("Exercise prompt")
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
        self.hint_btn.setAccessibleName("Show a hint")
        self.hint_btn.clicked.connect(self._show_hint)
        hint_layout.addWidget(self.hint_btn)
        self.hint_label = QLabel("")
        self.hint_label.setWordWrap(True)
        self.hint_label.setObjectName("Hint")
        hint_layout.addWidget(self.hint_label, 1)
        self.hint_row.hide()
        # feedback sits inside a colored panel (green/red) so the result is
        # signalled by panel + icon + words, never color alone
        self.feedback_panel = QFrame()
        fp_lay = QVBoxLayout(self.feedback_panel)
        fp_lay.setContentsMargins(14, 10, 14, 10)
        self.feedback = QLabel("")
        self.feedback.setWordWrap(True)
        self.feedback.setTextFormat(Qt.TextFormat.RichText)
        self.feedback.setAccessibleName("Feedback")
        fp_lay.addWidget(self.feedback)
        self.feedback_panel.hide()
        self.next_btn = QPushButton("Next  \u2192")
        self.next_btn.clicked.connect(self._next)
        self.next_btn.hide()
        for w in (self.badge, self.prompt, self.staff, self.audio_row, self.input_host,
                  self.hint_row, self.feedback_panel, self.next_btn):
            self._root.addWidget(w)
        self._root.addStretch(1)

    # -- load --------------------------------------------------------------
    def set_exercise(self, ex: Exercise, *, on_answer: Callable = None,
                     on_next: Callable = None, badge: str = "",
                     show_next: bool = True, show_feedback: bool = True) -> None:
        self.ex = ex
        self._on_answer = on_answer
        self._on_next = on_next
        self._show_next = show_next
        self._show_fb = show_feedback
        self._entry, self._seq, self._rhythm = [], [], []
        self._voices, self._voice_idx = [], 0
        self._answered = False
        self._picked_btn = None
        self._t0 = time.time()
        self.badge.setText(badge or f"{ex.domain.title()}  \u00b7  difficulty {ex.difficulty:.1f}")
        self.prompt.setText(ex.prompt)
        self.feedback.setText("")
        self.feedback_panel.hide()
        self.next_btn.hide()
        self.next_btn.setAccessibleDescription("")
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
            btn = QPushButton(f"{label}  (R)")
            btn.setToolTip("Keyboard shortcut: R")
            btn.setAccessibleName("Play the audio. Unlimited replays, shortcut R")
            btn.clicked.connect(self._play)
            self.audio_layout.addWidget(btn)
            replay = QPushButton("\u21BB Replay")
            replay.setObjectName("Secondary")
            replay.setToolTip("Keyboard shortcut: R")
            replay.setAccessibleName("Replay the audio")
            replay.clicked.connect(self._play)
            self.audio_layout.addWidget(replay)
            if self.ex.domain == "aural":
                speed = QComboBox()
                speed.setAccessibleName("Playback speed")
                speed.setToolTip("Slow the example down without changing pitch")
                for text, factor in _SPEED_OPTIONS:
                    speed.addItem(text, factor)
                current = min(range(len(_SPEED_OPTIONS)),
                              key=lambda i: abs(_SPEED_OPTIONS[i][1] - self._tempo_factor))
                speed.setCurrentIndex(current)
                speed.currentIndexChanged.connect(
                    lambda i, box=speed: setattr(self, "_tempo_factor", float(box.itemData(i))))
                self.audio_layout.addWidget(speed)
            self.audio_layout.addStretch(1)
            self.audio_row.show()
            if self.ex.domain == "aural":
                self._play()
        else:
            self.audio_row.hide()

    @guard("ExercisePlayer._play")
    def _play(self) -> None:
        if self.engine and self.ex and self.ex.play:
            spec = self.ex.play
            if self._tempo_factor != 1.0 and isinstance(spec, dict):
                spec = dict(spec)
                spec["tempo"] = max(20, int(spec.get("tempo", 90) * self._tempo_factor))
            render_play(self.engine, spec)

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
        elif mode == InputMode.MULTI_VOICE:
            self._build_multi_voice()

    def _build_choices(self) -> None:
        self._choice_btns = []
        for i, choice in enumerate(self.ex.choices):
            # number prefix surfaces the existing 1-9 shortcuts; grading uses
            # the stored value, never the display text
            text = f"{i + 1}.   {choice}" if i < 9 else str(choice)
            b = QPushButton(text)
            b.setObjectName("Choice")
            b.setProperty("choiceValue", str(choice))
            b.setAccessibleName(f"Answer {i + 1}: {choice}")
            b.clicked.connect(lambda _=False, c=choice, btn=b: self._pick(btn, c))
            self.input_layout.addWidget(b)
            self._choice_btns.append(b)

    def _pick(self, btn: QPushButton, choice) -> None:
        self._picked_btn = btn
        self._grade(choice)

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
        self.entry_label.setAccessibleName("Notes entered so far")
        self.input_layout.addWidget(self.entry_label)
        self.entry_piano = self._make_entry_piano(48, 84)
        self.entry_piano.notePressed.connect(self._add_entry_note)
        self.input_layout.addWidget(self.entry_piano)
        row = QHBoxLayout()
        back = QPushButton("\u232B Backspace"); back.setObjectName("Secondary")
        back.setAccessibleName("Delete the last entered note")
        back.clicked.connect(self._backspace_entry)
        clear = QPushButton("Clear"); clear.setObjectName("Secondary")
        clear.setAccessibleName("Clear all entered notes")
        clear.clicked.connect(self._clear_entry)
        submit = QPushButton("Submit")
        submit.clicked.connect(lambda: self._grade(list(self._entry)))
        row.addWidget(back); row.addWidget(clear); row.addStretch(1); row.addWidget(submit)
        self.input_layout.addLayout(row)
        self._refresh_entry()

    def _make_entry_piano(self, low: int, high: int) -> PianoWidget:
        piano = PianoWidget(low, high)
        piano.setAccessibleName("On-screen piano keyboard")
        piano.setAccessibleDescription(
            "Click keys, play a MIDI keyboard, or use computer keys A through L; "
            "Z and X shift the octave down and up")
        return piano

    def _build_piano(self) -> None:
        self.entry_label = QLabel()
        self.entry_label.setAccessibleName("Notes entered so far")
        self.input_layout.addWidget(self.entry_label)
        self.entry_piano = self._make_entry_piano(48, 84)
        self.entry_piano.notePressed.connect(self._add_entry_note)
        self.input_layout.addWidget(self.entry_piano)
        if self.midi is not None:
            try:
                self.midi.noteOn.connect(self._midi_note)
            except Exception:  # noqa: BLE001
                pass
        row = QHBoxLayout()
        clear = QPushButton("Clear"); clear.setObjectName("Secondary")
        clear.setAccessibleName("Clear all entered notes")
        clear.clicked.connect(self._clear_entry)
        submit = QPushButton("Submit")
        submit.clicked.connect(lambda: self._grade(list(self._entry)))
        row.addWidget(clear); row.addStretch(1); row.addWidget(submit)
        self.input_layout.addLayout(row)
        self._refresh_entry()

    def _build_rhythm(self) -> None:
        self.entry_label = QLabel()
        self.entry_label.setAccessibleName("Rhythm entered so far")
        self.input_layout.addWidget(self.entry_label)
        grid = QHBoxLayout()
        for label, val in _DUR_LABELS:
            b = QPushButton(label); b.setObjectName("Choice")
            b.setAccessibleName(_DUR_NAMES.get(val, label))
            b.clicked.connect(lambda _=False, v=val: self._add_rhythm(v))
            grid.addWidget(b)
        self.input_layout.addLayout(grid)
        row = QHBoxLayout()
        back = QPushButton("\u232B"); back.setObjectName("Secondary")
        back.setAccessibleName("Delete the last duration")
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
        back.setAccessibleName("Delete the last item")
        back.clicked.connect(self._backspace_seq)
        submit = QPushButton("Submit")
        submit.clicked.connect(lambda: self._grade(list(self._seq)))
        row.addWidget(back); row.addStretch(1); row.addWidget(submit)
        self.input_layout.addLayout(row)
        self._refresh_seq()

    def _build_multi_voice(self) -> None:
        names = self.ex.tags.get("voice_names", ["Voice 1", "Voice 2"])
        given = self.ex.tags.get("given_first_each")
        self._voices = [[int(g)] if given else [] for g in (given or [None] * len(names))]
        self._voice_idx = 0
        # voice selector
        sel_row = QHBoxLayout()
        sel_row.addWidget(QLabel("Entering:"))
        self._voice_btns = []
        group = QButtonGroup(self)
        group.setExclusive(True)
        for i, nm in enumerate(names):
            b = QPushButton(nm)
            b.setCheckable(True)
            b.setObjectName("Choice")
            b.clicked.connect(lambda _=False, idx=i: self._select_voice(idx))
            sel_row.addWidget(b)
            group.addButton(b)
            self._voice_btns.append(b)
        self._voice_btns[0].setChecked(True)
        sel_row.addStretch(1)
        self.input_layout.addLayout(sel_row)
        self.entry_label = QLabel()
        self.entry_label.setTextFormat(Qt.TextFormat.RichText)
        self.entry_label.setAccessibleName("Notes entered per voice")
        self.input_layout.addWidget(self.entry_label)
        self.entry_piano = self._make_entry_piano(36, 84)
        self.entry_piano.notePressed.connect(self._add_voice_note)
        self.input_layout.addWidget(self.entry_piano)
        if self.midi is not None:
            try:
                self.midi.noteOn.connect(self._midi_voice_note)
            except Exception:  # noqa: BLE001
                pass
        row = QHBoxLayout()
        back = QPushButton("⌫ Backspace"); back.setObjectName("Secondary")
        back.setAccessibleName("Delete the last note in the active voice")
        back.clicked.connect(self._backspace_voice)
        clear = QPushButton("Clear voice"); clear.setObjectName("Secondary")
        clear.setAccessibleName("Clear the active voice")
        clear.clicked.connect(self._clear_voice)
        submit = QPushButton("Submit all voices")
        submit.clicked.connect(lambda: self._grade([list(v) for v in self._voices]))
        row.addWidget(back); row.addWidget(clear); row.addStretch(1); row.addWidget(submit)
        self.input_layout.addLayout(row)
        self._refresh_voices()

    def _select_voice(self, idx: int) -> None:
        self._voice_idx = idx
        self._refresh_voices()

    def _add_voice_note(self, midi: int) -> None:
        if self._answered or not self._voices:
            return
        self._voices[self._voice_idx].append(int(midi))
        if self.engine:
            self.engine.play_note(int(midi), dur=0.6)
        # auto-advance to the next voice once this line is full
        expected = self._expected_voice_len()
        if expected and len(self._voices[self._voice_idx]) >= expected \
                and self._voice_idx < len(self._voices) - 1:
            self._voice_idx += 1
            self._voice_btns[self._voice_idx].setChecked(True)
        self._refresh_voices()

    def _midi_voice_note(self, midi: int, _vel: int) -> None:
        self._add_voice_note(midi)

    def _expected_voice_len(self) -> int:
        ans = self.ex.answer if self.ex else None
        if isinstance(ans, (list, tuple)) and ans and isinstance(ans[0], (list, tuple)):
            return len(ans[0])
        return 0

    def _backspace_voice(self) -> None:
        v = self._voices[self._voice_idx] if self._voices else None
        given = self.ex.tags.get("given_first_each")
        floor = 1 if given else 0
        if v and len(v) > floor:
            v.pop()
            self._refresh_voices()

    def _clear_voice(self) -> None:
        if not self._voices:
            return
        given = self.ex.tags.get("given_first_each")
        self._voices[self._voice_idx] = [int(given[self._voice_idx])] if given else []
        self._refresh_voices()

    def _refresh_voices(self) -> None:
        names = self.ex.tags.get("voice_names", [])
        expected = self._expected_voice_len()
        rows = []
        for i, (nm, v) in enumerate(zip(names, self._voices)):
            text = " ".join(Note.from_midi(m).name for m in v) or "(empty)"
            count = f"  <span style='color:{TEXT_MUTED}'>[{len(v)}/{expected}]</span>" if expected else ""
            if i == self._voice_idx:
                rows.append(f"<b style='color:{ACCENT}'>▶ {nm} (entering):</b>  {text}{count}")
            else:
                rows.append(f"<b>{nm}:</b>  {text}{count}")
        self.entry_label.setText("<br>".join(rows))
        if hasattr(self, "entry_piano"):
            self.entry_piano.clear_highlight()
            if self._voices:
                self.entry_piano.highlight(self._voices[self._voice_idx], ACCENT)

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
        # never delete the given starting note in NOTE_ENTRY exercises
        floor = 1 if (self.ex is not None and self.ex.input_mode == InputMode.NOTE_ENTRY
                      and self.ex.tags.get("given_first") is not None) else 0
        if len(self._entry) > floor:
            self._entry.pop()
            self._refresh_entry()

    def _clear_entry(self) -> None:
        given = self.ex.tags.get("given_first")
        self._entry = [int(given)] if given is not None and self.ex.input_mode == InputMode.NOTE_ENTRY else []
        self._refresh_entry()

    def _refresh_entry(self) -> None:
        notes = [Note.from_midi(m) for m in self._entry]
        if notes:
            parts = [n.name for n in notes]
            if (self.ex is not None and self.ex.input_mode == InputMode.NOTE_ENTRY
                    and self.ex.tags.get("given_first") is not None):
                parts[0] = f"<span style='color:{TEXT_MUTED}'>{parts[0]} (given)</span>"
            self.entry_label.setText("Your entry:  " + " ".join(parts))
        else:
            self.entry_label.setText(
                f"Your entry:  <span style='color:{TEXT_MUTED}'>(play or click notes)</span>")
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
        glyphs = "  ".join(_DUR_GLYPHS.get(v, str(v)) for v in self._rhythm)
        self.entry_label.setText(f"Rhythm:  {glyphs or '(empty)'}   "
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
        if getattr(self, "_show_fb", True):
            self._show_feedback(correct)
        else:
            self._show_neutral_feedback()
        if self._on_answer:
            self._on_answer(correct, elapsed_ms)

    def _show_neutral_feedback(self) -> None:
        """Assessment mode (placement): acknowledge without revealing
        right/wrong, so there is nothing time-pressured to read."""
        self.feedback.setText("Answer recorded ✓")
        self.feedback_panel.setObjectName("Card")
        style = self.feedback_panel.style()
        style.unpolish(self.feedback_panel)
        style.polish(self.feedback_panel)
        self.feedback_panel.show()
        if hasattr(self, "_choice_btns"):
            for b in self._choice_btns:
                b.setEnabled(False)

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
            plain = f"Correct! {self.ex.explanation}".strip()
            self.feedback.setText(
                f"<b style='color:{color}'>✓ Correct!</b>  {self.ex.explanation}")
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
                body += (f"<br><span style='color:{TEXT_MUTED}'>{teach}</span>")
            self.feedback.setText(f"<b style='color:{color}'>✗ Not quite.</b>  {body}")
            plain = "Not quite. " + " ".join(
                [f"The answer was {ans}." if ans else "", self.ex.explanation or "",
                 teach or ""]).strip()
        self.feedback_panel.setObjectName("FeedbackGood" if correct else "FeedbackBad")
        style = self.feedback_panel.style()
        style.unpolish(self.feedback_panel)
        style.polish(self.feedback_panel)
        self.feedback_panel.show()
        # reveal
        rev = self.ex.reveal or {}
        if "staff" in rev:
            self.staff.show()
            self.staff.set_clef(rev["staff"].get("clef", "treble"))
            self.staff.set_key_signature(rev["staff"].get("key_sig"))
            entered = [Note.from_midi(m) for m in self._entry] if self._entry else []
            self.staff.set_notes(entered, ghost=rev["staff"].get("notes", []))
        if "highlight" in rev and hasattr(self, "entry_piano"):
            self.entry_piano.flash(rev["highlight"], GOOD if correct else WARN)
        if hasattr(self, "_choice_btns"):
            answer = str(self.ex.answer)
            for b in self._choice_btns:
                b.setEnabled(False)
                if b.property("choiceValue") == answer:
                    b.setText("✓  " + b.text())
                    b.setProperty("result", "correct")
                elif b is self._picked_btn and not correct:
                    b.setText("✗  " + b.text())
                    b.setProperty("result", "wrong")
                b.style().unpolish(b)
                b.style().polish(b)
        if self._show_next:
            self.next_btn.show()
            # PyQt6 has no QAccessible.announce; instead the result rides on
            # the focus change every answer already triggers, so screen
            # readers speak it when Next takes focus.
            self.next_btn.setAccessibleDescription(plain)
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

    def _backspace_current(self) -> None:
        if self._answered or self.ex is None:
            return
        mode = self.ex.input_mode
        if mode in (InputMode.NOTE_ENTRY, InputMode.PIANO):
            self._backspace_entry()
        elif mode == InputMode.RHYTHM:
            self._backspace_rhythm()
        elif mode == InputMode.SEQUENCE:
            self._backspace_seq()
        elif mode == InputMode.MULTI_VOICE:
            self._backspace_voice()

    def _submit_current(self) -> None:
        if self.ex is None:
            return
        mode = self.ex.input_mode
        if mode == InputMode.MULTIPLE_CHOICE:
            # Enter activates the focused choice button (Space already works,
            # but Enter is what keyboard users expect)
            w = QApplication.focusWidget()
            if w in getattr(self, "_choice_btns", []):
                w.click()
            return
        if mode == InputMode.TEXT and hasattr(self, "text_edit"):
            self._grade(self.text_edit.text())
        elif mode in (InputMode.NOTE_ENTRY, InputMode.PIANO):
            self._grade(list(self._entry))
        elif mode == InputMode.RHYTHM:
            self._grade(list(self._rhythm))
        elif mode == InputMode.SEQUENCE:
            self._grade(list(self._seq))
        elif mode == InputMode.MULTI_VOICE:
            self._grade([list(v) for v in self._voices])

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
