"""Reference tools: an interactive circle of fifths, a staff/keyboard
explorer for any note/interval/scale/chord, and a glossary with playable
examples. The "look it up" side of the app: nothing here is graded."""

from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import (
    QAbstractItemView, QComboBox, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QSpinBox, QTableWidget, QTableWidgetItem, QTabWidget,
    QVBoxLayout, QWidget,
)

from ...errors import guard
from ...theory.chords import SEVENTH_QUALITIES, TRIAD_QUALITIES, seventh, triad
from ...theory.pitch import Note, transpose
from ...theory.scales import SCALE_TYPES, key_signature, scale_notes
from ...theory.neoriemann import nr_transform, parse_triad, triad_name, triad_pcs
from ...theory.settheory import (
    PCSet, forte_name, interval_vector, normal_form, parse_pitch_classes,
    pc_label, pc_name, prime_form,
)
from ...theory.twelvetone import matrix_labels, row_matrix
from .. import theme
from ..common import heading, subtle
from ..widgets import PianoWidget, StaffWidget

# circle order, majors clockwise from C at 12 o'clock; (major, relative minor)
_CIRCLE = [("C", "Am"), ("G", "Em"), ("D", "Bm"), ("A", "F#m"), ("E", "C#m"),
           ("B", "G#m"), ("F#", "D#m"), ("Db", "Bbm"), ("Ab", "Fm"),
           ("Eb", "Cm"), ("Bb", "Gm"), ("F", "Dm")]

_INTERVALS = [("Minor 2nd", 2, "m"), ("Major 2nd", 2, "M"), ("Minor 3rd", 3, "m"),
              ("Major 3rd", 3, "M"), ("Perfect 4th", 4, "P"), ("Tritone (A4)", 4, "A"),
              ("Perfect 5th", 5, "P"), ("Minor 6th", 6, "m"), ("Major 6th", 6, "M"),
              ("Minor 7th", 7, "m"), ("Major 7th", 7, "M"), ("Octave", 8, "P")]

_ROOTS = ["C", "C#", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]

GLOSSARY: list[tuple[str, str, dict | None]] = [
    ("Accidental", "A sharp, flat, or natural sign that raises or lowers a note by a half step, overriding the key signature for one measure.", None),
    ("Arpeggio", "The notes of a chord played one after another instead of together.", {"mode": "melody", "midis": [60, 64, 67, 72], "tempo": 140}),
    ("Augmented-sixth chord", "A chromatic predominant containing lowered scale degree 6 and raised scale degree 4; those tones normally expand outward to scale degree 5.", {"mode": "harmonic", "chords": [[44, 48, 54], [43, 47, 50]], "tempo": 70}),
    ("Cadence", "A two-chord punctuation mark ending a phrase. Authentic (V to I) sounds final; half (ending on V) sounds open.", {"mode": "harmonic", "chords": [[55, 59, 62, 67], [48, 52, 55, 60]], "tempo": 80}),
    ("Chord", "Three or more notes sounding together, usually built by stacking thirds.", {"mode": "chord", "midis": [60, 64, 67]}),
    ("Chromatic", "Moving by half steps, or using notes outside the current key.", {"mode": "melody", "midis": [60, 61, 62, 63, 64], "tempo": 160}),
    ("Circle of fifths", "All twelve keys arranged so each step clockwise adds a sharp (counterclockwise adds a flat). Neighboring keys share most of their notes.", None),
    ("Clef", "The symbol fixing which lines mean which pitches. Treble (G) clef wraps around G4; bass (F) clef's dots straddle F3.", None),
    ("Diatonic", "Using only the seven notes of the current key, nothing borrowed.", None),
    ("Doubling", "Giving one chord member to two SATB voices. The inversion, chord quality, and selected rule profile determine the preferred or required member.", None),
    ("Dominant", "The fifth scale degree, or the chord built on it (V). It leans hard toward the tonic.", {"mode": "harmonic", "chords": [[55, 59, 62], [48, 52, 55]], "tempo": 80}),
    ("Enharmonic", "Two names for the same sound, like F# and Gb. Spelling depends on the key's logic.", {"mode": "note", "midi": 66}),
    ("Figured bass", "Numbers under a bass note naming the intervals above it: 6 means first inversion, 6/4 second inversion.", None),
    ("Half step", "The smallest interval on the keyboard: one key to its nearest neighbor.", {"mode": "melody", "midis": [60, 61], "tempo": 120}),
    ("Harmonic minor", "Natural minor with the 7th raised, creating a leading tone (and an exotic step-and-a-half).", {"mode": "melody", "midis": [57, 59, 60, 62, 64, 65, 68, 69], "tempo": 130}),
    ("Interval", "The distance between two notes, named by letter count (number) and exact size (quality).", {"mode": "interval", "low": 60, "high": 67}),
    ("Inversion", "A chord rearranged so a note other than the root is lowest. The bass note defines it.", {"mode": "chord", "midis": [64, 67, 72]}),
    ("Key signature", "The sharps or flats at the start of each staff line, declaring the key once instead of marking every note.", None),
    ("Leading tone", "The 7th scale degree, a half step below the tonic, begging to resolve upward.", {"mode": "melody", "midis": [71, 72], "tempo": 100}),
    ("Ledger line", "A short extra line extending the staff above or below for high or low notes.", None),
    ("Major scale", "The do-re-mi pattern: whole and half steps in the order W-W-H-W-W-W-H.", {"mode": "melody", "midis": [60, 62, 64, 65, 67, 69, 71, 72], "tempo": 140}),
    ("Melodic minor", "Minor with raised 6th and 7th going up (smoothing the path to the tonic), natural form coming down.", {"mode": "melody", "midis": [57, 59, 60, 62, 64, 66, 68, 69], "tempo": 130}),
    ("Mode", "A scale built from the major pattern but starting on a different degree: Dorian on 2, Mixolydian on 5, and so on.", {"mode": "melody", "midis": [62, 64, 65, 67, 69, 71, 72, 74], "tempo": 140}),
    ("Modulation", "Changing key mid-piece, usually through a chord both keys share.", None),
    ("Neapolitan sixth", "A major triad on lowered scale degree 2, normally in first inversion with scale degree 4 doubled, moving toward dominant harmony.", {"mode": "harmonic", "chords": [[53, 56, 61], [55, 59, 62]], "tempo": 70}),
    ("Octave", "The interval between a note and the next note with the same name; double or half the frequency.", {"mode": "interval", "low": 60, "high": 72}),
    ("Pitch class", "A note name regardless of octave: every C on the piano belongs to pitch class C (0 in post-tonal numbering).", None),
    ("Pitch-class clock", "The twelve pitch classes arranged in chromatic semitone order, 0 through 11. Unlike the circle of fifths, adjacent positions are one half step apart.", None),
    ("Interval class", "The shortest distance between two pitch classes around the chromatic clock, numbered 1 through 6. Inversional partners share a class.", {"mode": "interval", "low": 60, "high": 67, "harmonic": True}),
    ("Interval-class vector", "A six-entry tally of every IC1, IC2, IC3, IC4, IC5, and IC6 pair inside a pitch-class collection.", None),
    ("Normal form", "The most compact cyclic ordering of a pitch-class set, preserving its actual transposition.", None),
    ("Prime form", "A canonical set-class representative beginning at 0, chosen by comparing a set's normal form with its inversion.", None),
    ("Forte number", "A catalog label written cardinality-ordinal, such as 3-11 for the major/minor triad set class.", None),
    ("Twelve-tone matrix", "A 12 by 12 table organizing a row's prime, inversion, retrograde, and retrograde-inversion forms.", None),
    ("Neo-Riemannian transformation", "A P, L, or R move between major/minor triads that holds two common tones and moves one pitch.", {"mode": "harmonic", "chords": [[60, 64, 67], [60, 63, 67]], "tempo": 68}),
    ("Tonnetz", "A geometric pitch network in which major and minor triads form neighbouring triangles and parsimonious voice leading becomes visible.", None),
    ("Parallel fifths", "The same two voices forming perfect fifths in consecutive chords while moving in the same direction; a standard SATB hard error.", {"mode": "harmonic", "chords": [[48, 55], [50, 57]], "tempo": 70}),
    ("Parallel octaves", "The same two voices moving in the same direction through consecutive octave-equivalent intervals, including unison-octave exchanges when a profile counts them.", {"mode": "harmonic", "chords": [[48, 60], [50, 62]], "tempo": 70}),
    ("Part writing", "Writing independent soprano, alto, tenor, and bass lines that realize a harmony. Validity depends on the selected voice-leading rule profile, not one universal textbook policy.", None),
    ("Relative minor", "The minor key sharing a major key's signature, rooted a minor 3rd below it (C major and A minor).", {"mode": "melody", "midis": [57, 59, 60, 62, 64, 65, 67, 69], "tempo": 140}),
    ("Resolution", "The release of tension: a dissonance or active tone moving to a stable one.", {"mode": "harmonic", "chords": [[55, 59, 62, 65], [48, 52, 55, 60]], "tempo": 70}),
    ("Roman numerals", "Chord labels by scale degree: uppercase for major (I, IV, V), lowercase for minor (ii, vi), degree sign for diminished.", None),
    ("Root", "The note a chord is built from and named after, regardless of which note is lowest.", None),
    ("Semitone", "Another name for the half step.", {"mode": "melody", "midis": [60, 61], "tempo": 120}),
    ("Seventh chord", "A triad plus the interval of a 7th above the root: four notes, more color and tension.", {"mode": "chord", "midis": [60, 64, 67, 70]}),
    ("Solfege", "Singing syllables for scale degrees: do re mi fa sol la ti. Movable-do follows the key.", None),
    ("SATB", "The four named chorale voices: soprano, alto, tenor, and bass. Voice identity remains fixed even when two parts share a pitch.", None),
    ("Staff", "The five lines and four spaces music is written on.", None),
    ("Subdominant", "The fourth scale degree or its chord (IV), a step away from home with a gentle lift.", {"mode": "harmonic", "chords": [[53, 57, 60], [48, 52, 55]], "tempo": 80}),
    ("Tonic", "Home base: the first scale degree, the note and chord everything resolves toward.", {"mode": "chord", "midis": [48, 52, 55, 60]}),
    ("Transposition", "Moving every note by the same interval, preserving the shape in a new key.", None),
    ("Triad", "The basic three-note chord: root, 3rd, 5th. Qualities: major, minor, diminished, augmented.", {"mode": "chord", "midis": [60, 64, 67]}),
    ("Tritone", "Three whole steps (augmented 4th / diminished 5th), the most restless interval in tonal music.", {"mode": "interval", "low": 60, "high": 66, "harmonic": True}),
    ("Whole step", "Two half steps, like C to D.", {"mode": "melody", "midis": [60, 62], "tempo": 120}),
    ("Voice leading", "How each named part moves from one chord to the next. Good voice leading preserves independence, resolves directed tones, and favors singable motion.", None),
]


class CircleOfFifthsWidget(QWidget):
    """Clickable two-ring circle: majors outside, relative minors inside."""

    keyPicked = pyqtSignal(int)   # index into _CIRCLE

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.selected = 0
        self.setMinimumSize(320, 320)
        self.setAccessibleName("Circle of fifths")
        self.setAccessibleDescription(
            "Twelve segments, one per key. Selected key: " + _CIRCLE[0][0] + " major.")

    def paintEvent(self, _event) -> None:  # noqa: N802 - Qt override
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        size = min(self.width(), self.height())
        cx, cy = self.width() / 2, self.height() / 2
        r_outer = size * 0.48
        r_mid = size * 0.34
        r_inner = size * 0.20
        seg = 360 / 12
        font_major = QFont()
        font_major.setPixelSize(max(11, int(size * 0.055)))
        font_major.setBold(True)
        font_minor = QFont()
        font_minor.setPixelSize(max(9, int(size * 0.04)))
        for i, (maj, rel) in enumerate(_CIRCLE):
            # segment i centered at angle (12 o'clock = C, clockwise)
            a0 = 90 - i * seg - seg / 2
            sel = (i == self.selected)
            fill = QColor(theme.ACCENT) if sel else QColor(theme.TOKENS["SURFACE_2"])
            if sel:
                fill.setAlpha(230)
            p.setPen(QPen(QColor(theme.BORDER), 1.2))
            p.setBrush(fill)
            p.drawPie(QRectF(cx - r_outer, cy - r_outer, r_outer * 2, r_outer * 2),
                      int(a0 * 16), int(seg * 16))
            # punch the inner hole later; draw labels along the mid radius
        # inner disc (background) to create the ring look
        p.setBrush(QColor(theme.SURFACE))
        p.setPen(QPen(QColor(theme.BORDER), 1.2))
        p.drawEllipse(QPointF(cx, cy), r_inner, r_inner)
        # labels
        for i, (maj, rel) in enumerate(_CIRCLE):
            ang = math.radians(90 - i * seg)
            sel = (i == self.selected)
            color = QColor(theme.TEXT_DARK) if sel else QColor(theme.TOKENS["TEXT"])
            p.setPen(color)
            p.setFont(font_major)
            x = cx + math.cos(ang) * (r_outer + r_mid) / 2
            y = cy - math.sin(ang) * (r_outer + r_mid) / 2
            p.drawText(QRectF(x - 30, y - 22, 60, 24), Qt.AlignmentFlag.AlignCenter, maj)
            p.setFont(font_minor)
            p.drawText(QRectF(x - 30, y + 0, 60, 18), Qt.AlignmentFlag.AlignCenter, rel)
        # center text: selected key
        p.setPen(QColor(theme.TOKENS["TEXT"]))
        f = QFont()
        f.setPixelSize(max(10, int(size * 0.045)))
        f.setBold(True)
        p.setFont(f)
        maj, rel = _CIRCLE[self.selected]
        p.drawText(QRectF(cx - r_inner, cy - r_inner, r_inner * 2, r_inner * 2),
                   Qt.AlignmentFlag.AlignCenter, f"{maj}\n{rel}")
        p.end()

    def mousePressEvent(self, e) -> None:  # noqa: N802 - Qt override
        cx, cy = self.width() / 2, self.height() / 2
        dx, dy = e.position().x() - cx, e.position().y() - cy
        size = min(self.width(), self.height())
        dist = math.hypot(dx, dy)
        if dist < size * 0.20 / 2 or dist > size * 0.48:
            return
        ang = math.degrees(math.atan2(-dy, dx))      # 0 = 3 o'clock, ccw positive
        idx = round((90 - ang) / 30) % 12
        self.selected = int(idx)
        maj, rel = _CIRCLE[self.selected]
        self.setAccessibleDescription(
            f"Selected key: {maj} major, relative minor {rel}.")
        self.keyPicked.emit(self.selected)
        self.update()


class PitchClassClockWidget(QWidget):
    """Clickable chromatic clock for selecting and rotating pc collections."""

    pcsChanged = pyqtSignal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.pcs: set[int] = {0, 4, 7}
        self.setMinimumSize(300, 300)
        self.setAccessibleName("Pitch-class clock")
        self._refresh_description()

    def set_pcs(self, pcs) -> None:
        self.pcs = {int(pc) % 12 for pc in pcs}
        self._refresh_description()
        self.update()

    def _refresh_description(self) -> None:
        labels = ", ".join(f"{pc_label(pc)} {pc_name(pc)}" for pc in sorted(self.pcs))
        self.setAccessibleDescription("Selected pitch classes: " + (labels or "none"))

    def paintEvent(self, _event) -> None:  # noqa: N802 - Qt override
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        size = min(self.width(), self.height())
        cx, cy = self.width() / 2, self.height() / 2
        radius = size * 0.36
        dot = max(18.0, size * 0.062)

        positions: dict[int, QPointF] = {}
        for pc in range(12):
            angle = math.radians(-90 + pc * 30)
            positions[pc] = QPointF(cx + math.cos(angle) * radius,
                                    cy + math.sin(angle) * radius)
        selected = sorted(self.pcs)
        if len(selected) > 1:
            p.setPen(QPen(QColor(theme.ACCENT), 2.2))
            for a, b in zip(selected, selected[1:] + selected[:1]):
                p.drawLine(positions[a], positions[b])

        font = QFont()
        font.setPixelSize(max(10, int(size * 0.038)))
        font.setBold(True)
        p.setFont(font)
        for pc, point in positions.items():
            active = pc in self.pcs
            p.setPen(QPen(QColor(theme.BORDER), 1.2))
            p.setBrush(QColor(theme.ACCENT if active else theme.TOKENS["SURFACE_2"]))
            p.drawEllipse(point, dot, dot)
            p.setPen(QColor(theme.TEXT_DARK if active else theme.TOKENS["TEXT"]))
            p.drawText(QRectF(point.x() - dot, point.y() - dot, dot * 2, dot * 2),
                       Qt.AlignmentFlag.AlignCenter, pc_label(pc))
            p.setPen(QColor(theme.TOKENS["TEXT_MUTED"]))
            p.drawText(QRectF(point.x() - 26, point.y() + dot, 52, 18),
                       Qt.AlignmentFlag.AlignCenter, pc_name(pc))

        p.setPen(QColor(theme.TOKENS["TEXT"]))
        center = "{" + " ".join(pc_label(pc) for pc in selected) + "}"
        p.drawText(QRectF(cx - 80, cy - 28, 160, 56), Qt.AlignmentFlag.AlignCenter,
                   center or "empty")
        p.end()

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt override
        cx, cy = self.width() / 2, self.height() / 2
        dx, dy = event.position().x() - cx, event.position().y() - cy
        radius = min(self.width(), self.height()) * 0.36
        if abs(math.hypot(dx, dy) - radius) > min(self.width(), self.height()) * 0.13:
            return
        angle = math.degrees(math.atan2(dy, dx))
        pc = round((angle + 90) / 30) % 12
        if pc in self.pcs:
            self.pcs.remove(pc)
        else:
            self.pcs.add(pc)
        self._refresh_description()
        self.pcsChanged.emit(sorted(self.pcs))
        self.update()


class ReferenceScreen(QWidget):
    def __init__(self, ctx, parent=None) -> None:
        super().__init__(parent)
        self.ctx = ctx
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 16)
        root.setSpacing(10)
        root.addWidget(heading("Reference"))
        tabs = QTabWidget()
        tabs.addTab(self._build_circle_tab(), "Circle of fifths")
        tabs.addTab(self._build_explorer_tab(), "Explorer")
        tabs.addTab(self._build_posttonal_tab(), "Post-tonal bridge")
        tabs.addTab(self._build_glossary_tab(), "Glossary")
        self.tabs = tabs
        root.addWidget(tabs, 1)

    # -- circle of fifths ---------------------------------------------------
    def _build_circle_tab(self) -> QWidget:
        page = QWidget()
        lay = QHBoxLayout(page)
        self.circle = CircleOfFifthsWidget()
        self.circle.keyPicked.connect(self._on_key_picked)
        lay.addWidget(self.circle, 1)

        side = QVBoxLayout()
        self.key_title = QLabel("")
        self.key_title.setObjectName("H2")
        side.addWidget(self.key_title)
        self.key_info = subtle("")
        self.key_info.setWordWrap(True)
        side.addWidget(self.key_info)
        self.key_staff = StaffWidget("treble")
        side.addWidget(self.key_staff)
        row = QHBoxLayout()
        play_scale = QPushButton("▶ Scale")
        play_scale.setAccessibleName("Play the selected key's scale")
        play_scale.clicked.connect(self._play_key_scale)
        play_chords = QPushButton("▶ I IV V I")
        play_chords.setAccessibleName("Play the selected key's primary chords")
        play_chords.setObjectName("Secondary")
        play_chords.clicked.connect(self._play_key_chords)
        row.addWidget(play_scale)
        row.addWidget(play_chords)
        row.addStretch(1)
        side.addLayout(row)
        side.addStretch(1)
        lay.addLayout(side, 1)
        self._on_key_picked(0)
        return page

    @guard("Reference._on_key_picked")
    def _on_key_picked(self, idx: int) -> None:
        maj, rel = _CIRCLE[idx]
        tonic = Note.parse(maj + "4")
        sig = key_signature(tonic, "major")
        self.key_title.setText(f"{maj} major  ·  {rel.replace('m', '')} minor")
        if sig["count"]:
            acc = "♯" if sig["kind"] == "sharp" else "♭"
            sig_text = f"{sig['count']} {acc}: " + ", ".join(sig["letters"])
        else:
            sig_text = "no sharps or flats"
        notes = scale_notes(tonic, "major", octaves=1)
        chords = " · ".join(f"{n.letter}{'#' if n.alter == 1 else 'b' if n.alter == -1 else ''}"
                            for n in (notes[0], notes[3], notes[4], notes[5]))
        self.key_info.setText(
            f"Key signature: {sig_text}.\nRelative minor: {rel} (same signature).\n"
            f"Primary chords: I={chords.split(' · ')[0]}  IV={chords.split(' · ')[1]}  "
            f"V={chords.split(' · ')[2]}  vi={chords.split(' · ')[3]}m")
        self.key_staff.set_key_signature(sig)
        self.key_staff.set_notes([])

    @guard("Reference._play_key_scale")
    def _play_key_scale(self) -> None:
        maj, _ = _CIRCLE[self.circle.selected]
        tonic = Note.parse(maj + "4")
        notes = scale_notes(tonic, "major", octaves=1)
        midis = [n.midi for n in notes] + [notes[0].midi + 12]
        self.ctx.engine.play_melody(midis, tempo=150)
        self.key_staff.set_notes(notes)

    @guard("Reference._play_key_chords")
    def _play_key_chords(self) -> None:
        maj, _ = _CIRCLE[self.circle.selected]
        tonic = Note.parse(maj + "3")
        notes = scale_notes(tonic, "major", octaves=1)
        chords = []
        for deg in (0, 3, 4, 0):
            ch = triad(notes[deg], "major" if deg != 5 else "minor")
            chords.append(([n.midi for n in ch.voiced(3)], 2.0))
        self.ctx.engine.play_sequence(chords, tempo=84)

    # -- explorer -------------------------------------------------------------
    def _build_explorer_tab(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.addWidget(subtle("Pick anything; see it on the staff and keyboard, then hear it."))
        controls = QHBoxLayout()
        self.ex_root = QComboBox()
        self.ex_root.setAccessibleName("Root note")
        for r in _ROOTS:
            self.ex_root.addItem(r)
        controls.addWidget(QLabel("Root:"))
        controls.addWidget(self.ex_root)
        self.ex_kind = QComboBox()
        self.ex_kind.setAccessibleName("What to show")
        for kind in ("Interval", "Scale / mode", "Triad", "Seventh chord"):
            self.ex_kind.addItem(kind)
        self.ex_kind.currentIndexChanged.connect(self._refill_subtypes)
        controls.addWidget(self.ex_kind)
        self.ex_sub = QComboBox()
        self.ex_sub.setAccessibleName("Specific type")
        controls.addWidget(self.ex_sub, 1)
        show = QPushButton("Show && play")
        show.clicked.connect(self._explore)
        controls.addWidget(show)
        controls.addStretch(1)
        lay.addLayout(controls)
        self.ex_label = QLabel("")
        self.ex_label.setObjectName("BodyLg")
        lay.addWidget(self.ex_label)
        self.ex_staff = StaffWidget("treble")
        lay.addWidget(self.ex_staff)
        self.ex_piano = PianoWidget(48, 84)
        self.ex_piano.setMinimumHeight(130)
        lay.addWidget(self.ex_piano)
        lay.addStretch(1)
        self._refill_subtypes()
        return page

    def _refill_subtypes(self) -> None:
        kind = self.ex_kind.currentIndex()
        self.ex_sub.clear()
        if kind == 0:
            for label, num, q in _INTERVALS:
                self.ex_sub.addItem(label, (num, q))
        elif kind == 1:
            for st in SCALE_TYPES:
                self.ex_sub.addItem(st.replace("_", " ").title(), st)
        elif kind == 2:
            for q in TRIAD_QUALITIES:
                self.ex_sub.addItem(q.title(), q)
        else:
            for q in SEVENTH_QUALITIES:
                self.ex_sub.addItem(q, q)

    @guard("Reference._explore")
    def _explore(self) -> None:
        root_name = self.ex_root.currentText()
        root = Note.parse(root_name + "4")
        kind = self.ex_kind.currentIndex()
        data = self.ex_sub.currentData()
        if data is None:
            return
        if kind == 0:
            num, q = data
            try:
                top = transpose(root, num, q)
            except KeyError:
                self.ex_label.setText("That interval cannot be spelled from this root.")
                return
            notes = [root, top]
            self.ex_label.setText(f"{self.ex_sub.currentText()} above {root_name}: "
                                  f"{root.name} → {top.name}")
            self.ctx.engine.play_interval(root.midi, top.midi)
        elif kind == 1:
            notes = scale_notes(root, data, octaves=1)
            self.ex_label.setText(" ".join(n.name_no_octave for n in notes))
            self.ctx.engine.play_melody([n.midi for n in notes] + [root.midi + 12], tempo=150)
        else:
            ch = triad(root, data) if kind == 2 else seventh(root, data)
            notes = ch.voiced(4)
            self.ex_label.setText(f"{ch.symbol}:  " + " ".join(n.name_no_octave for n in notes))
            self.ctx.engine.play_chord([n.midi for n in notes])
        self.ex_staff.set_notes(notes)
        self.ex_piano.flash([n.midi for n in notes], theme.ACCENT)

    # -- pre-graduate post-tonal workbench -----------------------------------
    def _build_posttonal_tab(self) -> QWidget:
        page = QWidget()
        outer = QHBoxLayout(page)
        outer.setContentsMargins(6, 6, 6, 6)
        outer.setSpacing(14)

        left = QVBoxLayout()
        intro = subtle(
            "Bridge from tonal analysis to graduate work: use 0-11 pitch classes, "
            "then connect the clock to sets, hearing, staff/keyboard realization, "
            "rows, and P/L/R voice leading. Click clock positions to edit the set.")
        intro.setWordWrap(True)
        left.addWidget(intro)
        self.pc_clock = PitchClassClockWidget()
        self.pc_clock.pcsChanged.connect(self._post_clock_changed)
        left.addWidget(self.pc_clock, 1)

        set_row = QHBoxLayout()
        self.pc_input = QLineEdit("0 4 7")
        self.pc_input.setAccessibleName("Pitch-class collection")
        self.pc_input.setPlaceholderText("0 4 7  or  C E G")
        self.pc_input.returnPressed.connect(self._post_analyze)
        analyze = QPushButton("Analyze set")
        analyze.clicked.connect(self._post_analyze)
        set_row.addWidget(QLabel("Set:"))
        set_row.addWidget(self.pc_input, 1)
        set_row.addWidget(analyze)
        left.addLayout(set_row)

        self.pc_result = QLabel("")
        self.pc_result.setWordWrap(True)
        self.pc_result.setTextFormat(Qt.TextFormat.RichText)
        self.pc_result.setAccessibleName("Pitch-class set analysis")
        left.addWidget(self.pc_result)

        transform_row = QHBoxLayout()
        self.pc_op = QComboBox()
        self.pc_op.addItems(["Tn", "TnI"])
        self.pc_n = QSpinBox()
        self.pc_n.setRange(0, 11)
        self.pc_n.setValue(2)
        apply_transform = QPushButton("Apply transform")
        apply_transform.clicked.connect(self._post_transform)
        play_chord = QPushButton("▶ Chord")
        play_chord.clicked.connect(lambda: self._post_play_collection(False))
        play_arp = QPushButton("▶ Arpeggiate")
        play_arp.clicked.connect(lambda: self._post_play_collection(True))
        transform_row.addWidget(self.pc_op)
        transform_row.addWidget(self.pc_n)
        transform_row.addWidget(apply_transform)
        transform_row.addWidget(play_chord)
        transform_row.addWidget(play_arp)
        left.addLayout(transform_row)

        self.pc_piano = PianoWidget(48, 83)
        self.pc_piano.setMinimumHeight(105)
        left.addWidget(self.pc_piano)
        outer.addLayout(left, 1)

        right = QVBoxLayout()
        row_title = QLabel("Twelve-tone row matrix")
        row_title.setObjectName("H3")
        right.addWidget(row_title)
        right.addWidget(subtle("Enter a permutation of 0-11. P reads across; I down; R and RI reverse those directions."))
        row_controls = QHBoxLayout()
        self.row_input = QLineEdit("0 1 4 2 7 3 9 5 11 6 10 8")
        self.row_input.setAccessibleName("Twelve-tone prime row")
        build = QPushButton("Build matrix")
        build.clicked.connect(self._post_build_matrix)
        row_controls.addWidget(self.row_input, 1)
        row_controls.addWidget(build)
        right.addLayout(row_controls)
        self.matrix_info = QLabel("")
        self.matrix_info.setWordWrap(True)
        self.matrix_info.setAccessibleName("Twelve-tone matrix status")
        right.addWidget(self.matrix_info)
        self.matrix_table = QTableWidget(12, 12)
        self.matrix_table.setAccessibleName("Twelve-tone matrix")
        self.matrix_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.matrix_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.matrix_table.horizontalHeader().setDefaultSectionSize(28)
        self.matrix_table.verticalHeader().setDefaultSectionSize(24)
        right.addWidget(self.matrix_table, 1)

        plr_title = QLabel("Neo-Riemannian P/L/R")
        plr_title.setObjectName("H3")
        right.addWidget(plr_title)
        plr_row = QHBoxLayout()
        self.plr_start = QComboBox()
        for root_name in ("C", "Cm", "Db", "Dbm", "D", "Dm", "E", "Em", "F", "Fm",
                          "F#", "F#m", "G", "Gm", "Ab", "Abm", "A", "Am", "Bb", "Bbm", "B", "Bm"):
            self.plr_start.addItem(root_name)
        self.plr_ops = QLineEdit("PLR")
        self.plr_ops.setMaximumWidth(80)
        self.plr_ops.setAccessibleName("P L R transformation chain")
        apply_plr = QPushButton("Transform")
        apply_plr.clicked.connect(self._post_apply_plr)
        play_plr = QPushButton("▶ Path")
        play_plr.clicked.connect(self._post_play_plr)
        plr_row.addWidget(self.plr_start)
        plr_row.addWidget(self.plr_ops)
        plr_row.addWidget(apply_plr)
        plr_row.addWidget(play_plr)
        right.addLayout(plr_row)
        self.plr_result = QLabel("")
        self.plr_result.setAccessibleName("P L R result")
        right.addWidget(self.plr_result)
        outer.addLayout(right, 1)

        self._post_pcs = [0, 4, 7]
        self._plr_path = []
        self._post_analyze()
        self._post_build_matrix()
        self._post_apply_plr()
        return page

    def _post_clock_changed(self, pcs) -> None:
        self.pc_input.setText(" ".join(pc_label(pc) for pc in pcs))
        self._post_analyze()

    @guard("Reference._post_analyze")
    def _post_analyze(self) -> None:
        try:
            pcs = parse_pitch_classes(self.pc_input.text())
            if not pcs:
                raise ValueError("select or enter at least one pitch class")
        except ValueError as exc:
            self.pc_result.setText(f"<b>Input problem:</b> {exc}")
            return
        self._post_pcs = pcs
        self.pc_clock.set_pcs(pcs)
        self.pc_piano.highlight([60 + pc for pc in pcs], theme.ACCENT)
        nf = normal_form(pcs)
        pf = prime_form(pcs)
        vector = interval_vector(pcs)
        names = " · ".join(f"{pc_label(pc)}={pc_name(pc)}" for pc in sorted(set(pcs)))
        self.pc_result.setText(
            f"<b>Pitch classes:</b> {{{' '.join(pc_label(pc) for pc in sorted(set(pcs)))}}}  "
            f"({names})<br><b>Normal form:</b> [{' '.join(pc_label(pc) for pc in nf)}]  "
            f"<b>Prime form:</b> ({''.join(pc_label(pc) for pc in pf)})  "
            f"<b>Forte:</b> {forte_name(tuple(pf))}<br>"
            f"<b>IC vector:</b> &lt;{' '.join(str(x) for x in vector)}&gt;")

    @guard("Reference._post_transform")
    def _post_transform(self) -> None:
        current = PCSet.of(self._post_pcs)
        n = self.pc_n.value()
        result = current.TnI(n) if self.pc_op.currentText() == "TnI" else current.Tn(n)
        self.pc_input.setText(" ".join(pc_label(pc) for pc in result.pcs))
        self._post_analyze()

    @guard("Reference._post_play_collection")
    def _post_play_collection(self, arpeggiate: bool = False) -> None:
        midis = [60 + pc for pc in sorted(set(self._post_pcs))]
        self.ctx.engine.play_chord(midis, arpeggiate=arpeggiate, tempo=90)
        self.pc_piano.flash(midis, theme.ACCENT)

    @guard("Reference._post_build_matrix")
    def _post_build_matrix(self) -> None:
        try:
            row = parse_pitch_classes(self.row_input.text(), unique=False)
            if sorted(row) != list(range(12)):
                raise ValueError("a row must contain every pitch class 0-11 exactly once")
            matrix = row_matrix(row)
        except (ValueError, IndexError) as exc:
            self.matrix_info.setText(f"Enter each pitch class exactly once: {exc}")
            return
        labels = matrix_labels(row)
        self.matrix_table.setHorizontalHeaderLabels(labels["top"])
        self.matrix_table.setVerticalHeaderLabels(labels["left"])
        for r, values in enumerate(matrix):
            for c, value in enumerate(values):
                item = QTableWidgetItem(pc_label(value))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.matrix_table.setItem(r, c, item)
        self.matrix_info.setText(
            "Built 12×12 matrix. Row headers are P forms; column headers are I forms. "
            "Read the same lines backward for R and RI.")

    @guard("Reference._post_apply_plr")
    def _post_apply_plr(self) -> None:
        start = parse_triad(self.plr_start.currentText())
        ops = self.plr_ops.text().upper().replace(" ", "")
        if not ops or any(op not in "PLR" for op in ops):
            self.plr_result.setText("Enter a chain containing only P, L, and R.")
            self._plr_path = []
            return
        path = [start]
        current = start
        for op in ops:
            current = nr_transform(current, op)
            path.append(current)
        self._plr_path = path
        names = [triad_name(t) for t in path]
        self.plr_result.setText(" → ".join(names) + "  (" + " · ".join(ops) + ")")

    @guard("Reference._post_play_plr")
    def _post_play_plr(self) -> None:
        self._post_apply_plr()
        if not self._plr_path:
            return
        items = [([60 + pc for pc in triad_pcs(t)], 2.0) for t in self._plr_path]
        self.ctx.engine.play_sequence(items, tempo=68)
        self.pc_piano.flash(items[-1][0], theme.ACCENT)

    # -- glossary -------------------------------------------------------------
    def _build_glossary_tab(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search terms…")
        self.search.setAccessibleName("Search the glossary")
        self.search.textChanged.connect(self._filter_glossary)
        lay.addWidget(self.search)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        host = QWidget()
        self.gloss_layout = QVBoxLayout(host)
        self.gloss_layout.setSpacing(8)
        self._gloss_rows: list[tuple[str, QWidget]] = []
        for term, definition, play in GLOSSARY:
            row = QWidget()
            rlay = QHBoxLayout(row)
            rlay.setContentsMargins(4, 2, 4, 2)
            text = QLabel(f"<b>{term}</b><br>{definition}")
            text.setWordWrap(True)
            text.setTextFormat(Qt.TextFormat.RichText)
            rlay.addWidget(text, 1)
            if play:
                btn = QPushButton("▶")
                btn.setObjectName("Secondary")
                btn.setFixedWidth(44)
                btn.setAccessibleName(f"Play an example of {term}")
                btn.clicked.connect(lambda _=False, spec=play: self._play_example(spec))
                rlay.addWidget(btn, alignment=Qt.AlignmentFlag.AlignTop)
            self.gloss_layout.addWidget(row)
            self._gloss_rows.append((term.lower() + " " + definition.lower(), row))
        self.gloss_layout.addStretch(1)
        scroll.setWidget(host)
        lay.addWidget(scroll, 1)
        return page

    def _filter_glossary(self, text: str) -> None:
        needle = text.strip().lower()
        for haystack, row in self._gloss_rows:
            row.setVisible(not needle or needle in haystack)

    @guard("Reference._play_example")
    def _play_example(self, spec: dict) -> None:
        from ...exercises.base import render_play
        render_play(self.ctx.engine, spec)
