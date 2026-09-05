"""Free piano workspace: play the on-screen keyboard (or a connected MIDI
keyboard), and audition scales and chords in any key."""

from __future__ import annotations

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTabWidget,
    QVBoxLayout, QWidget,
)

from ...theory.pitch import Note
from ...theory.scales import SCALE_TYPES, scale_notes
from ...theory.chords import triad, seventh
from ...theory.neoriemann import nr_transform, parse_triad, triad_name, triad_pcs
from ...theory.settheory import parse_pitch_classes, pc_label, pc_name
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
                              "Use the tonal workspace or bridge numbers, sets, rows, "
                              "and P/L/R transformations into keyboard sound."))

        tabs = QTabWidget()
        tabs.setAccessibleName("Piano workspace mode")
        tonal = QWidget()
        tonal_layout = QVBoxLayout(tonal)

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
        tonal_layout.addLayout(ctrl)

        self.readout = QLabel("")
        self.readout.setObjectName("BodyLg")
        self.readout.setAccessibleName("Played notes readout")
        tonal_layout.addWidget(self.readout)

        self.piano = PianoWidget(36, 96)
        self.piano.setMinimumHeight(180)
        self.piano.notePressed.connect(self._on_press)
        self.piano.noteReleased.connect(self._on_release)
        tonal_layout.addWidget(self.piano, 1)
        tabs.addTab(tonal, "Tonal")
        tabs.addTab(self._build_pregraduate_tab(), "Pre-Graduate")
        self.tabs = tabs
        root.addWidget(tabs, 1)

    def on_show(self) -> None:
        if self.ctx.midi is not None and not self._midi_connected:
            try:
                self.ctx.midi.noteOn.connect(self._on_midi)
                self._midi_connected = True
            except Exception:  # noqa: BLE001
                pass

    def _build_pregraduate_tab(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        help_text = subtle(
            "Pitch-class work ignores octave but row work preserves order. Use T for "
            "10 and E for 11 in compact numeric notation; note names also work.")
        help_text.setWordWrap(True)
        lay.addWidget(help_text)

        set_row = QHBoxLayout()
        self.pg_set_input = QLineEdit("0 4 7")
        self.pg_set_input.setAccessibleName("Pitch-class set to realize")
        self.pg_set_input.setPlaceholderText("0 4 7  or  C E G")
        play_set = QPushButton("Play set as chord")
        play_set.clicked.connect(self._play_pc_collection)
        arp_set = QPushButton("Arpeggiate set")
        arp_set.clicked.connect(lambda: self._play_pc_collection(True))
        set_row.addWidget(QLabel("Pitch-class set:"))
        set_row.addWidget(self.pg_set_input, 1)
        set_row.addWidget(play_set)
        set_row.addWidget(arp_set)
        lay.addLayout(set_row)

        row_row = QHBoxLayout()
        self.pg_row_input = QLineEdit("0 1 4 2 7 3")
        self.pg_row_input.setAccessibleName("Ordered row segment to play")
        play_row = QPushButton("Play row segment")
        play_row.clicked.connect(self._play_row_segment)
        row_row.addWidget(QLabel("Ordered row:"))
        row_row.addWidget(self.pg_row_input, 1)
        row_row.addWidget(play_row)
        lay.addLayout(row_row)

        plr_row = QHBoxLayout()
        self.pg_plr_start = QComboBox()
        for name in ("C", "Cm", "D", "Dm", "E", "Em", "F", "Fm", "F#", "F#m",
                     "G", "Gm", "Ab", "Abm", "A", "Am", "Bb", "Bbm", "B", "Bm"):
            self.pg_plr_start.addItem(name)
        self.pg_plr_ops = QLineEdit("PLR")
        self.pg_plr_ops.setMaximumWidth(90)
        self.pg_plr_ops.setAccessibleName("P L R transformation chain")
        play_plr = QPushButton("Play P/L/R path")
        play_plr.clicked.connect(self._play_plr_path)
        plr_row.addWidget(QLabel("Triad:"))
        plr_row.addWidget(self.pg_plr_start)
        plr_row.addWidget(QLabel("Operations:"))
        plr_row.addWidget(self.pg_plr_ops)
        plr_row.addWidget(play_plr)
        plr_row.addStretch(1)
        lay.addLayout(plr_row)

        self.pg_readout = QLabel(
            "Start with a collection, ordered row segment, or parsimonious triad path.")
        self.pg_readout.setObjectName("BodyLg")
        self.pg_readout.setWordWrap(True)
        self.pg_readout.setAccessibleName("Pre-graduate piano analysis")
        lay.addWidget(self.pg_readout)
        self.pg_piano = PianoWidget(36, 96)
        self.pg_piano.setMinimumHeight(180)
        self.pg_piano.notePressed.connect(self._on_pg_press)
        self.pg_piano.noteReleased.connect(lambda _midi: QTimer.singleShot(
            180, self.pg_piano.clear_highlight))
        lay.addWidget(self.pg_piano, 1)
        return page

    def _on_pg_press(self, midi: int) -> None:
        self.ctx.engine.play_note(int(midi), dur=0.9)
        self.pg_piano.highlight([int(midi)], theme.ACCENT)
        note = Note.from_midi(int(midi))
        self.pg_readout.setText(
            f"{note.name} · pitch class {note.pc} ({pc_label(note.pc)}) · MIDI {midi}")

    def _play_pc_collection(self, arpeggiate: bool = False) -> None:
        try:
            pcs = parse_pitch_classes(self.pg_set_input.text())
            if not pcs:
                raise ValueError("enter at least one pitch class")
        except ValueError as exc:
            self.pg_readout.setText(f"Input problem: {exc}")
            return
        midis = [60 + pc for pc in sorted(set(pcs))]
        self.ctx.engine.play_chord(midis, arpeggiate=arpeggiate, tempo=90)
        self.pg_piano.flash(midis, theme.ACCENT)
        self.pg_readout.setText(
            "Set {" + " ".join(pc_label(pc) for pc in sorted(set(pcs))) + "}: "
            + " · ".join(f"{pc_label(pc)}={pc_name(pc)}" for pc in sorted(set(pcs)))
            + ". Any octave/register preserves the pitch-class set.")

    def _play_row_segment(self) -> None:
        try:
            pcs = parse_pitch_classes(self.pg_row_input.text(), unique=False)
            if not 2 <= len(pcs) <= 12:
                raise ValueError("enter 2 to 12 pitch classes")
            if len(set(pcs)) != len(pcs):
                raise ValueError("a row segment cannot repeat a pitch class")
        except ValueError as exc:
            self.pg_readout.setText(f"Input problem: {exc}")
            return
        midis = [60 + pc for pc in pcs]
        self.ctx.engine.play_melody(midis, tempo=108, beats_per_note=0.75)
        self.pg_piano.flash(midis, theme.ACCENT)
        self.pg_readout.setText(
            "Ordered row: " + " – ".join(pc_label(pc) for pc in pcs)
            + "  |  notes: " + " – ".join(pc_name(pc) for pc in pcs)
            + ". Register and rhythm remain free compositional choices.")

    def _play_plr_path(self) -> None:
        try:
            start = parse_triad(self.pg_plr_start.currentText())
            ops = self.pg_plr_ops.text().upper().replace(" ", "")
            if not ops or any(op not in "PLR" for op in ops):
                raise ValueError("use only P, L, and R")
        except ValueError as exc:
            self.pg_readout.setText(f"Input problem: {exc}")
            return
        path = [start]
        current = start
        for op in ops:
            current = nr_transform(current, op)
            path.append(current)
        items = [([60 + pc for pc in triad_pcs(t)], 2.0) for t in path]
        self.ctx.engine.play_sequence(items, tempo=68)
        self.pg_piano.flash(items[-1][0], theme.ACCENT)
        self.pg_readout.setText(
            " → ".join(triad_name(t) for t in path)
            + ". Each basic move retains two common tones and changes one pitch.")

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
