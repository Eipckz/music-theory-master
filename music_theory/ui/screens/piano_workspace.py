"""Free piano workspace: play the on-screen keyboard (or a connected MIDI
keyboard), and audition scales and chords in any key."""

from __future__ import annotations

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from ...theory.pitch import Note
from ...theory.scales import SCALE_TYPES, scale_notes
from ...theory.chords import triad, seventh
from ..common import heading, subtle
from .. import theme
from ..widgets import PianoWidget

_ROOTS = [("C", 0), ("D\u266d", ("D", -1)), ("D", 0), ("E\u266d", ("E", -1)), ("E", 0),
          ("F", 0), ("F\u266f", ("F", 1)), ("G", 0), ("A\u266d", ("A", -1)), ("A", 0),
          ("B\u266d", ("B", -1)), ("B", 0)]
_TRIADS = ["major", "minor", "diminished", "augmented"]
_SEVENTHS = ["dom7", "maj7", "min7", "halfdim7", "dim7"]


def _root_note(spec, octave=4) -> Note:
    if isinstance(spec, tuple):
        return Note(spec[0], spec[1], octave)
    return Note(spec, 0, octave)


class PianoWorkspaceScreen(QWidget):
    def __init__(self, ctx, parent=None) -> None:
        super().__init__(parent)
        self.ctx = ctx
        self._midi_connected = False
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 20)
        root.setSpacing(12)
        root.addWidget(heading("Piano"))
        root.addWidget(subtle("Click keys (or play your MIDI keyboard) to hear them. "
                              "Use the controls to audition scales and chords."))

        ctrl = QHBoxLayout()
        self.root_combo = QComboBox()
        for label, _ in _ROOTS:
            self.root_combo.addItem(label)
        ctrl.addWidget(QLabel("Root:"))
        ctrl.addWidget(self.root_combo)

        self.scale_combo = QComboBox()
        for st in SCALE_TYPES:
            self.scale_combo.addItem(st.replace("_", " "), st)
        ctrl.addWidget(self.scale_combo)
        play_scale = QPushButton("Play scale")
        play_scale.clicked.connect(self._play_scale)
        ctrl.addWidget(play_scale)

        self.chord_combo = QComboBox()
        for q in _TRIADS + _SEVENTHS:
            self.chord_combo.addItem(q, q)
        ctrl.addWidget(self.chord_combo)
        play_chord = QPushButton("Play chord")
        play_chord.clicked.connect(self._play_chord)
        ctrl.addWidget(play_chord)
        ctrl.addStretch(1)
        root.addLayout(ctrl)

        self.readout = QLabel("")
        self.readout.setObjectName("BodyLg")
        self.readout.setAccessibleName("Played notes readout")
        root.addWidget(self.readout)

        self.piano = PianoWidget(36, 96)
        self.piano.setMinimumHeight(180)
        self.piano.notePressed.connect(self._on_press)
        self.piano.noteReleased.connect(self._on_release)
        root.addWidget(self.piano, 1)

    def on_show(self) -> None:
        if self.ctx.midi is not None and not self._midi_connected:
            try:
                self.ctx.midi.noteOn.connect(self._on_midi)
                self._midi_connected = True
            except Exception:  # noqa: BLE001
                pass

    def _on_press(self, midi: int) -> None:
        self.ctx.engine.play_note(int(midi), dur=0.9)
        self.piano.highlight([int(midi)], theme.ACCENT)
        n = Note.from_midi(int(midi))
        self.readout.setText(f"{n.name}  (MIDI {midi})")

    def _on_release(self, midi: int) -> None:
        QTimer.singleShot(180, self.piano.clear_highlight)

    def _on_midi(self, midi: int, _vel: int) -> None:
        self._on_press(int(midi))
        QTimer.singleShot(300, self.piano.clear_highlight)

    def _play_scale(self) -> None:
        spec = _ROOTS[self.root_combo.currentIndex()][1]
        st = self.scale_combo.currentData()
        notes = scale_notes(_root_note(spec), st, octaves=1)
        notes = notes + [Note(notes[0].letter, notes[0].alter, notes[0].octave + 1)]
        midis = [n.midi for n in notes]
        self.ctx.engine.play_melody(midis, tempo=120)
        self.piano.flash(midis, theme.ACCENT)
        self.readout.setText(" ".join(n.name_no_octave for n in notes))

    def _play_chord(self) -> None:
        spec = _ROOTS[self.root_combo.currentIndex()][1]
        q = self.chord_combo.currentData()
        ch = seventh(_root_note(spec), q) if q in _SEVENTHS else triad(_root_note(spec), q)
        voiced = ch.voiced(4)
        midis = [n.midi for n in voiced]
        self.ctx.engine.play_chord(midis)
        self.piano.flash(midis, theme.ACCENT)
        self.readout.setText(f"{ch.symbol}:  " + " ".join(n.name_no_octave for n in voiced))
