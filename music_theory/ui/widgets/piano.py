"""Interactive on-screen piano keyboard widget.

Emits notePressed/noteReleased with MIDI numbers, supports highlighting (for
showing prompts/answers), and an optional computer-keyboard mapping. Used by
the piano workspace, dictation input, and many exercises."""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QMouseEvent, QPainter, QPen
from PyQt6.QtWidgets import QWidget

_WHITE_PCS = {0, 2, 4, 5, 7, 9, 11}
_BLACK_PCS = {1, 3, 6, 8, 10}
# Offset of each black key relative to the white key it follows.
_BLACK_AFTER = {1: 0, 3: 1, 6: 3, 8: 4, 10: 5}  # pc -> white index within octave

_PC_NAMES = {0: "C", 2: "D", 4: "E", 5: "F", 7: "G", 9: "A", 11: "B"}

# Computer-keyboard mapping (one octave starting at the keyboard's base).
_KEYMAP = {
    Qt.Key.Key_A: 0, Qt.Key.Key_W: 1, Qt.Key.Key_S: 2, Qt.Key.Key_E: 3,
    Qt.Key.Key_D: 4, Qt.Key.Key_F: 5, Qt.Key.Key_T: 6, Qt.Key.Key_G: 7,
    Qt.Key.Key_Y: 8, Qt.Key.Key_H: 9, Qt.Key.Key_U: 10, Qt.Key.Key_J: 11,
    Qt.Key.Key_K: 12, Qt.Key.Key_O: 13, Qt.Key.Key_L: 14,
}


class PianoWidget(QWidget):
    notePressed = pyqtSignal(int)
    noteReleased = pyqtSignal(int)

    def __init__(self, low_midi: int = 48, high_midi: int = 84, parent=None) -> None:
        super().__init__(parent)
        self.low_midi = low_midi
        self.high_midi = high_midi
        self._highlight: dict[int, QColor] = {}
        self._pressed: set[int] = set()
        self._kb_base = 60
        self.show_labels = True
        self.setMinimumHeight(110)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._white_midis = [m for m in range(low_midi, high_midi + 1) if m % 12 in _WHITE_PCS]

    # -- public API -------------------------------------------------------
    def set_range(self, low_midi: int, high_midi: int) -> None:
        self.low_midi, self.high_midi = low_midi, high_midi
        self._white_midis = [m for m in range(low_midi, high_midi + 1) if m % 12 in _WHITE_PCS]
        self.update()

    def highlight(self, midis, color: str = "#4caf50") -> None:
        c = QColor(color)
        for m in midis:
            self._highlight[m] = c
        self.update()

    def clear_highlight(self) -> None:
        self._highlight.clear()
        self.update()

    def flash(self, midis, color: str = "#4caf50") -> None:
        self.clear_highlight()
        self.highlight(midis, color)

    # -- geometry ---------------------------------------------------------
    def _white_width(self) -> float:
        n = max(1, len(self._white_midis))
        return self.width() / n

    def _white_rect(self, index: int) -> QRectF:
        w = self._white_width()
        return QRectF(index * w, 0, w, self.height())

    def _black_rect(self, white_index: int) -> QRectF:
        w = self._white_width()
        bw = w * 0.62
        x = (white_index + 1) * w - bw / 2
        return QRectF(x, 0, bw, self.height() * 0.62)

    def _black_keys(self):
        """Yield (midi, white_index_before) for visible black keys."""
        out = []
        for i, wm in enumerate(self._white_midis[:-1]):
            pc = wm % 12
            if pc in (0, 2, 5, 7, 9):  # C D F G A are followed by a black key
                bm = wm + 1
                if self.low_midi <= bm <= self.high_midi:
                    out.append((bm, i))
        return out

    # -- painting ---------------------------------------------------------
    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        font = QFont()
        font.setPointSize(7)
        p.setFont(font)
        for i, wm in enumerate(self._white_midis):
            rect = self._white_rect(i)
            if wm in self._highlight:
                p.fillRect(rect, self._highlight[wm])
            elif wm in self._pressed:
                p.fillRect(rect, QColor("#90caf9"))
            else:
                p.fillRect(rect, QColor("#fafafa"))
            p.setPen(QPen(QColor("#444"), 1))
            p.drawRect(rect)
            if self.show_labels and wm % 12 == 0:
                p.setPen(QColor("#888"))
                p.drawText(
                    rect.adjusted(2, 0, -2, -4),
                    Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
                    f"C{wm // 12 - 1}",
                )
        for bm, wi in self._black_keys():
            rect = self._black_rect(wi)
            if bm in self._highlight:
                p.fillRect(rect, self._highlight[bm].darker(110))
            elif bm in self._pressed:
                p.fillRect(rect, QColor("#1565c0"))
            else:
                p.fillRect(rect, QColor("#202020"))
            p.setPen(QPen(QColor("#000"), 1))
            p.drawRect(rect)
        p.end()

    # -- hit testing ------------------------------------------------------
    def _midi_at(self, x: float, y: float) -> Optional[int]:
        for bm, wi in self._black_keys():
            if self._black_rect(wi).contains(x, y):
                return bm
        w = self._white_width()
        idx = int(x // w)
        if 0 <= idx < len(self._white_midis):
            return self._white_midis[idx]
        return None

    def mousePressEvent(self, e: QMouseEvent) -> None:
        midi = self._midi_at(e.position().x(), e.position().y())
        if midi is not None:
            self._press(midi)

    def mouseReleaseEvent(self, e: QMouseEvent) -> None:
        for m in list(self._pressed):
            self._release(m)

    def keyPressEvent(self, e) -> None:
        if e.isAutoRepeat():
            return
        off = _KEYMAP.get(e.key())
        if off is not None:
            self._press(self._kb_base + off)
        else:
            super().keyPressEvent(e)

    def keyReleaseEvent(self, e) -> None:
        if e.isAutoRepeat():
            return
        off = _KEYMAP.get(e.key())
        if off is not None:
            self._release(self._kb_base + off)

    def _press(self, midi: int) -> None:
        if midi not in self._pressed:
            self._pressed.add(midi)
            self.notePressed.emit(midi)
            self.update()

    def _release(self, midi: int) -> None:
        if midi in self._pressed:
            self._pressed.discard(midi)
            self.noteReleased.emit(midi)
            self.update()
