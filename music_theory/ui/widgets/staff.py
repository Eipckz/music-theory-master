"""Music staff widget: renders spelled notes at correct positions (treble,
bass, or grand staff) with accidentals and ledger lines, and supports
click-to-place note entry for melodic dictation."""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QWidget

from ...theory.pitch import LETTERS, Note

# Diatonic index of the bottom staff line per clef.
_BOTTOM_REF = {"treble": Note("E", 0, 4).diatonic_index, "bass": Note("G", 0, 2).diatonic_index}
_ACC_GLYPH = {-2: "\U0001D12B", -1: "\u266d", 0: "\u266e", 1: "\u266f", 2: "\U0001D12A"}
_CLEF_GLYPH = {"treble": "\U0001D11E", "bass": "\U0001D122"}

# Standard key-signature staff positions (steps above bottom line) per clef.
_SHARP_STEPS = {"treble": [8, 5, 9, 6, 3, 7, 4], "bass": [6, 3, 7, 4, 1, 5, 2]}
_FLAT_STEPS = {"treble": [4, 7, 3, 6, 2, 5, 1], "bass": [2, 5, 1, 4, 0, 3, -1]}


class StaffWidget(QWidget):
    noteAdded = pyqtSignal(object)   # emits a Note
    noteRemoved = pyqtSignal(int)

    def __init__(self, clef: str = "treble", parent=None) -> None:
        super().__init__(parent)
        self.clef = clef                      # 'treble' | 'bass' | 'grand'
        self.notes: list[Note] = []
        self.ghost_notes: list[Note] = []     # second-color overlay (e.g. answer)
        self.key_sig: Optional[dict] = None
        self.allow_input = False
        self.input_alter = 0
        self.prefer_sharps = True
        self.line_spacing = 12
        self.setMinimumHeight(170)

    # -- public API -------------------------------------------------------
    def set_clef(self, clef: str) -> None:
        self.clef = clef
        self.update()

    def set_notes(self, notes, ghost=None) -> None:
        self.notes = [self._as_note(n) for n in notes]
        self.ghost_notes = [self._as_note(n) for n in (ghost or [])]
        self.update()

    def clear(self) -> None:
        self.notes = []
        self.ghost_notes = []
        self.update()

    def set_key_signature(self, key_sig: Optional[dict]) -> None:
        self.key_sig = key_sig
        self.update()

    def pop_note(self) -> None:
        if self.notes:
            removed = self.notes.pop()
            self.noteRemoved.emit(removed.midi)
            self.update()

    def _as_note(self, n) -> Note:
        if isinstance(n, Note):
            return n
        return Note.from_midi(int(n), self.prefer_sharps)

    # -- geometry helpers -------------------------------------------------
    def _staff_tops(self) -> list[tuple[str, float]]:
        """Return [(clef, bottom_line_y)] for each staff to draw."""
        if self.clef == "grand":
            top = 30
            return [("treble", top + 4 * self.line_spacing), ("bass", top + 9 * self.line_spacing)]
        return [(self.clef, self.height() / 2 + 2 * self.line_spacing)]

    def _y_for(self, note: Note, clef: str, bottom_y: float) -> float:
        steps = note.diatonic_index - _BOTTOM_REF[clef]
        return bottom_y - steps * (self.line_spacing / 2)

    def _choose_clef(self, note: Note) -> tuple[str, float]:
        staves = self._staff_tops()
        if len(staves) == 1:
            return staves[0]
        # grand staff: middle C and above on treble, below on bass
        return staves[0] if note.midi >= 60 else staves[1]

    # -- painting ---------------------------------------------------------
    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.fillRect(self.rect(), QColor("#fbfbf7"))
        ls = self.line_spacing
        left = 12
        right = self.width() - 12
        clef_font = QFont()
        clef_font.setPixelSize(int(ls * 6))
        glyph_font = QFont()
        glyph_font.setPixelSize(int(ls * 2.2))

        x_start = left + 46
        for clef, bottom_y in self._staff_tops():
            p.setPen(QPen(QColor("#333"), 1))
            for i in range(5):
                y = bottom_y - i * ls
                p.drawLine(left, int(y), right, int(y))
            # clef glyph
            p.setFont(clef_font)
            p.setPen(QColor("#222"))
            cy = bottom_y - 4 * ls if clef == "treble" else bottom_y - 4 * ls
            p.drawText(QPointF(left + 2, bottom_y - (0.5 if clef == "treble" else 1.5) * ls),
                       _CLEF_GLYPH.get(clef, "?"))
            # key signature
            kx = left + 40
            if self.key_sig and self.key_sig.get("count"):
                p.setFont(glyph_font)
                steps_list = (_SHARP_STEPS if self.key_sig["kind"] == "sharp" else _FLAT_STEPS)[clef]
                glyph = "\u266f" if self.key_sig["kind"] == "sharp" else "\u266d"
                for k in range(self.key_sig["count"]):
                    yy = bottom_y - steps_list[k] * (ls / 2)
                    p.drawText(QPointF(kx, yy + ls * 0.4), glyph)
                    kx += ls
            x_start = max(x_start, kx + 8)

        # draw notes left-to-right; ghost (answer) aligns by index with entry
        count = max(1, len(self.notes), len(self.ghost_notes))
        span = right - x_start - 24
        step_x = max(24.0, min(64.0, span / count))
        for i, note in enumerate(self.ghost_notes):
            clef, bottom_y = self._choose_clef(note)
            self._draw_note(p, note, x_start + 14 + i * step_x, clef, bottom_y, glyph_font, True)
        for i, note in enumerate(self.notes):
            clef, bottom_y = self._choose_clef(note)
            self._draw_note(p, note, x_start + 14 + i * step_x, clef, bottom_y, glyph_font, False)
        p.end()

    def _draw_note(self, p: QPainter, note: Note, x: float, clef: str, bottom_y: float,
                   glyph_font: QFont, ghost: bool) -> None:
        y = self._y_for(note, clef, bottom_y)
        ls = self.line_spacing
        color = QColor("#bbbbbb") if ghost else QColor("#111")
        # ledger lines
        steps = note.diatonic_index - _BOTTOM_REF[clef]
        p.setPen(QPen(color, 1))
        if steps < 0:
            k = -2
            while k >= steps:
                ly = bottom_y - k * (ls / 2)
                p.drawLine(int(x - ls * 0.9), int(ly), int(x + ls * 0.9), int(ly))
                k -= 2
        elif steps > 8:
            k = 10
            while k <= steps:
                ly = bottom_y - k * (ls / 2)
                p.drawLine(int(x - ls * 0.9), int(ly), int(x + ls * 0.9), int(ly))
                k += 2
        # notehead
        p.setBrush(color)
        p.setPen(QPen(color, 1))
        rw, rh = ls * 0.8, ls * 0.62
        p.drawEllipse(QRectF(x - rw / 2, y - rh / 2, rw, rh))
        # stem
        p.drawLine(int(x + rw / 2), int(y), int(x + rw / 2), int(y - ls * 3))
        # accidental
        if note.alter != 0:
            p.setFont(glyph_font)
            p.drawText(QPointF(x - ls * 1.6, y + ls * 0.4), _ACC_GLYPH[note.alter])

    # -- click input ------------------------------------------------------
    def mousePressEvent(self, e) -> None:
        if not self.allow_input:
            return
        clef, bottom_y = self._staff_tops()[0]
        if self.clef == "grand":
            staves = self._staff_tops()
            clef, bottom_y = min(staves, key=lambda s: abs(e.position().y() - s[1]))
        step = round((bottom_y - e.position().y()) / (self.line_spacing / 2))
        dia = _BOTTOM_REF[clef] + int(step)
        letter = LETTERS[dia % 7]
        octave = dia // 7
        note = Note(letter, self.input_alter, octave)
        self.notes.append(note)
        self.noteAdded.emit(note)
        self.update()
