"""SATB-aware notation preview with preserved voice identity."""

from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QWidget

from ...theory.part_writing.models import Clef, Layout, Voice, VOICE_ORDER, Voicing
from ...theory.pitch import LETTERS, Note
from ...theory.scales import key_fifths
from .. import theme
from .staff import _music_font


_BOTTOM_REF = {
    "treble": Note.parse("E4").diatonic_index,
    "bass": Note.parse("G2").diatonic_index,
    "alto": Note.parse("F3").diatonic_index,
    "tenor": Note.parse("D3").diatonic_index,
}
_CLEF = {"treble": "\U0001D11E", "bass": "\U0001D122",
         "alto": "\U0001D121", "tenor": "\U0001D121"}
_ACC = {-2: "𝄫", -1: "♭", 1: "♯", 2: "𝄪"}
_SHARP_STEPS = {
    "treble": [8, 5, 9, 6, 3, 7, 4], "bass": [6, 3, 7, 4, 1, 5, 2],
    "alto": [7, 4, 8, 5, 2, 6, 3], "tenor": [2, 6, 3, 7, 4, 8, 5],
}
_FLAT_STEPS = {
    "treble": [4, 7, 3, 6, 2, 5, 1], "bass": [2, 5, 1, 4, 0, 3, -1],
    "alto": [3, 6, 2, 5, 1, 4, 0], "tenor": [5, 8, 4, 7, 3, 6, 2],
}
_VOICE_STYLE = {
    Voice.SOPRANO: ("treble", True),
    Voice.ALTO: ("treble", False),
    Voice.TENOR: ("bass", True),
    Voice.BASS: ("bass", False),
}


class SatbStaffWidget(QWidget):
    """Render four named voices, including independent unisons and stems."""

    noteRequested = pyqtSignal(int, object, object)  # slot, Voice, Note
    slotSelected = pyqtSignal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.voicings: list[Voicing] = []
        self.ghost_voicings: list[Voicing] = []
        self.harmony_labels: list[str] = []
        self.figured_bass: list[str] = []
        self.durations: list[float] = []
        self.meter = (4, 4)
        self.key_tonic = "C"
        self.key_mode = "major"
        self.key_signature_fifths = 0
        self.layout_mode = Layout.CHORALE
        self.clefs = {voice: Clef(_VOICE_STYLE[voice][0]) for voice in VOICE_ORDER}
        self.locked: set[tuple[int, Voice]] = set()
        self.generated: set[tuple[int, Voice]] = set()
        self.violations: set[tuple[int, Voice]] = set()
        self.selected_slot = 0
        self.selected_voice = Voice.SOPRANO
        self.line_spacing = 15
        self.setAccessibleName("SATB score")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def minimumSizeHint(self) -> QSize:  # noqa: N802
        height = 440 if self.layout_mode == Layout.OPEN_SCORE else 285
        return QSize(560, height)

    def set_score(self, voicings: list[Voicing], *, labels=None, figures=None,
                  durations=None, ghost=None, locked=None, generated=None,
                  violations=None) -> None:
        self.voicings = list(voicings)
        self.ghost_voicings = list(ghost or [])
        self.harmony_labels = list(labels or [])
        self.figured_bass = list(figures or [])
        self.durations = [float(value) for value in (durations or [])]
        self.locked = set(locked or ())
        self.generated = set(generated or ())
        self.violations = set(violations or ())
        self._update_accessibility()
        self.updateGeometry()
        self.update()

    def set_layout_mode(self, mode: Layout | str) -> None:
        self.layout_mode = mode if isinstance(mode, Layout) else Layout(mode)
        self.updateGeometry()
        self.update()

    def set_meter(self, numerator: int, denominator: int) -> None:
        self.meter = (int(numerator), int(denominator))
        self.update()

    def set_key(self, tonic: str, mode: str) -> None:
        self.key_tonic = str(tonic)
        self.key_mode = str(mode)
        self.key_signature_fifths = key_fifths(
            Note.parse(self.key_tonic + "4"), self.key_mode)
        self._update_accessibility()
        self.update()

    def set_clefs(self, clefs: dict[Voice, Clef | str]) -> None:
        for voice, clef in clefs.items():
            self.clefs[voice] = clef if isinstance(clef, Clef) else Clef(clef)
        self._update_accessibility()
        self.updateGeometry()
        self.update()

    def set_selection(self, slot: int, voice: Voice) -> None:
        self.selected_slot = max(0, int(slot))
        self.selected_voice = voice
        self.update()

    def _update_accessibility(self) -> None:
        columns = []
        for index, voicing in enumerate(self.voicings):
            details = ", ".join(
                f"{voice.value} {voicing[voice].name} in {self.clefs[voice].value} clef"
                for voice in VOICE_ORDER)
            label = self.harmony_labels[index] if index < len(self.harmony_labels) else ""
            columns.append(f"Slot {index + 1}{f' {label}' if label else ''}: {details}")
        if self.ghost_voicings:
            columns.append("A ghost answer overlay is visible.")
        prefix = f"Key {self.key_tonic} {self.key_mode}, meter {self.meter[0]}/{self.meter[1]}. "
        self.setAccessibleDescription(prefix + (". ".join(columns) if columns else "No notes entered"))

    def _systems(self):
        ls = self.line_spacing
        if self.layout_mode == Layout.OPEN_SCORE:
            top = 28.0
            return [
                (Voice.SOPRANO, self.clefs[Voice.SOPRANO].value, top + 4 * ls),
                (Voice.ALTO, self.clefs[Voice.ALTO].value, top + 10.5 * ls),
                (Voice.TENOR, self.clefs[Voice.TENOR].value, top + 17.0 * ls),
                (Voice.BASS, self.clefs[Voice.BASS].value, top + 23.5 * ls),
            ]
        top = 36.0
        return [(None, "treble", top + 4 * ls), (None, "bass", top + 12 * ls)]

    def _bottom_for(self, voice: Voice) -> tuple[str, float]:
        systems = self._systems()
        if self.layout_mode == Layout.OPEN_SCORE:
            for system_voice, clef, bottom in systems:
                if system_voice == voice:
                    return clef, bottom
        clef = _VOICE_STYLE[voice][0]
        for _, system_clef, bottom in systems:
            if system_clef == clef:
                return clef, bottom
        return systems[0][1], systems[0][2]

    def _y(self, note: Note, clef: str, bottom: float) -> float:
        return bottom - (note.diatonic_index - _BOTTOM_REF[clef]) * self.line_spacing / 2

    def _column_x(self, index: int) -> float:
        left = self._notation_left()
        count = max(1, len(self.voicings), len(self.ghost_voicings))
        usable = max(80.0, self.width() - left - 30.0)
        return left + (index + 0.5) * usable / count

    def _notation_left(self) -> float:
        return 108.0 + abs(self.key_signature_fifths) * 9.0

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        paper = QColor(theme.STAFF_PAPER)
        ink = QColor(theme.STAFF_INK)
        painter.setBrush(paper)
        painter.setPen(QPen(QColor(theme.BORDER), 1))
        painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 9, 9)
        ls = self.line_spacing
        systems = self._systems()
        clef_font = _music_font(int(ls * 5.1))
        painter.setFont(clef_font)
        for system_voice, clef, bottom in systems:
            painter.setPen(QPen(ink, 1.2))
            for line in range(5):
                y = bottom - line * ls
                painter.drawLine(QPointF(46, y), QPointF(self.width() - 18, y))
            painter.drawText(QPointF(49, bottom - (0.55 if clef == "treble" else 1.45) * ls),
                             _CLEF[clef])
            self._draw_key_signature(painter, clef, bottom, ink)
            if system_voice is not None:
                label_font = QFont()
                label_font.setPixelSize(11)
                label_font.setBold(True)
                painter.setFont(label_font)
                painter.drawText(QPointF(8, bottom - 1.6 * ls), system_voice.value.title())
                painter.setFont(clef_font)
        self._draw_meter(painter, systems, ink)
        for index, voicing in enumerate(self.ghost_voicings):
            self._draw_voicing(painter, index, voicing, ghost=True)
        for index, voicing in enumerate(self.voicings):
            self._draw_voicing(painter, index, voicing, ghost=False)
        self._draw_barlines(painter, systems, ink)
        self._draw_labels(painter, systems, ink)
        painter.end()

    def _draw_key_signature(self, painter: QPainter, clef: str,
                            bottom: float, ink: QColor) -> None:
        count = abs(self.key_signature_fifths)
        if not count:
            return
        alter = 1 if self.key_signature_fifths > 0 else -1
        steps = (_SHARP_STEPS if alter > 0 else _FLAT_STEPS)[clef]
        font = _music_font(19)
        painter.setFont(font)
        painter.setPen(ink)
        for index in range(min(7, count)):
            y = bottom - steps[index] * self.line_spacing / 2
            painter.drawText(QPointF(72 + index * 9, y + 6), _ACC[alter])

    def _draw_meter(self, painter: QPainter, systems, ink: QColor) -> None:
        font = QFont()
        font.setPixelSize(15)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(ink)
        x = 76 + abs(self.key_signature_fifths) * 9
        for _, _clef, bottom in systems:
            painter.drawText(QPointF(x, bottom - 2.35 * self.line_spacing), str(self.meter[0]))
            painter.drawText(QPointF(x, bottom - 0.35 * self.line_spacing), str(self.meter[1]))

    def _draw_voicing(self, painter: QPainter, index: int, voicing: Voicing,
                      *, ghost: bool) -> None:
        x = self._column_x(index)
        for voice in VOICE_ORDER:
            note = voicing[voice]
            clef, bottom = self._bottom_for(voice)
            y = self._y(note, clef, bottom)
            stem_up = _VOICE_STYLE[voice][1]
            offset = 0.0
            for other in VOICE_ORDER:
                if other == voice:
                    continue
                if voicing[other].midi == note.midi \
                        and VOICE_ORDER.index(other) < VOICE_ORDER.index(voice):
                    offset = self.line_spacing * 0.72
            self._draw_note(painter, index, voice, note, x + offset, y,
                            clef, bottom, stem_up, ghost)

    def _draw_note(self, painter: QPainter, index: int, voice: Voice, note: Note,
                   x: float, y: float, clef: str, bottom: float,
                   stem_up: bool, ghost: bool) -> None:
        ls = self.line_spacing
        color = QColor("#777777") if ghost else QColor(theme.STAFF_INK)
        if not ghost and (index, voice) in self.violations:
            color = QColor(theme.BAD)
        elif not ghost and (index, voice) in self.locked:
            color = QColor(theme.ACCENT)
        elif not ghost and (index, voice) in self.generated:
            color = QColor(theme.GOOD)
        if not ghost and index == self.selected_slot and voice == self.selected_voice:
            highlight = QColor(theme.ACCENT)
            highlight.setAlpha(55)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(highlight)
            painter.drawRoundedRect(QRectF(x - 12, y - 9, 24, 18), 5, 5)
        steps = note.diatonic_index - _BOTTOM_REF[clef]
        painter.setPen(QPen(color, 1.2))
        ledgers = range(-2, steps - 1, -2) if steps < 0 else range(10, steps + 1, 2)
        for ledger in ledgers:
            ly = bottom - ledger * ls / 2
            painter.drawLine(QPointF(x - 10, ly), QPointF(x + 10, ly))
        painter.save()
        painter.translate(x, y)
        painter.rotate(-18)
        painter.setPen(QPen(color, 1.4))
        painter.setBrush(color)
        painter.drawEllipse(QRectF(-7.2, -4.6, 14.4, 9.2))
        painter.restore()
        stem_x = x + 6.2 if stem_up else x - 6.2
        painter.setPen(QPen(color, 1.5))
        if stem_up:
            painter.drawLine(QPointF(stem_x, y), QPointF(stem_x, y - 42))
        else:
            painter.drawLine(QPointF(stem_x, y), QPointF(stem_x, y + 42))
        if note.alter:
            font = _music_font(20)
            painter.setFont(font)
            painter.drawText(QPointF(x - 21, y + 6), _ACC[note.alter])
        if not ghost and (index, voice) in self.locked:
            font = QFont()
            font.setPixelSize(9)
            painter.setFont(font)
            painter.drawText(QPointF(x + 9, y - 7), "LOCK")

    def _draw_barlines(self, painter: QPainter, systems, ink: QColor) -> None:
        if not self.durations or not self.voicings:
            return
        beats_per_bar = self.meter[0] * 4 / self.meter[1]
        total = 0.0
        painter.setPen(QPen(ink, 1.2))
        top = min(bottom - 4 * self.line_spacing for _, _, bottom in systems)
        low = max(bottom for _, _, bottom in systems)
        for index, duration in enumerate(self.durations[:len(self.voicings)]):
            total += duration
            if total >= beats_per_bar - 1e-6:
                total = 0.0
                bx = (self._column_x(index) + self._column_x(index + 1)) / 2 \
                    if index + 1 < len(self.voicings) else self.width() - 21
                painter.drawLine(QPointF(bx, top), QPointF(bx, low))

    def _draw_labels(self, painter: QPainter, systems, ink: QColor) -> None:
        font = QFont()
        font.setPixelSize(11)
        painter.setFont(font)
        painter.setPen(ink)
        bottom = max(item[2] for item in systems)
        for index in range(max(len(self.voicings), len(self.harmony_labels))):
            x = self._column_x(index)
            label = self.harmony_labels[index] if index < len(self.harmony_labels) else ""
            figure = self.figured_bass[index] if index < len(self.figured_bass) else ""
            if label:
                painter.drawText(QPointF(x - 12, bottom + 24), label)
            if figure:
                painter.drawText(QPointF(x - 7, bottom + 40), figure)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        count = max(1, len(self.voicings), len(self.ghost_voicings))
        left = self._notation_left()
        slot = min(count - 1, max(0, round((event.position().x() - left)
                                           / max(1, self.width() - left - 30) * count - 0.5)))
        self.selected_slot = slot
        self.slotSelected.emit(slot)
        clef, bottom = self._bottom_for(self.selected_voice)
        step = round((bottom - event.position().y()) / (self.line_spacing / 2))
        diatonic = _BOTTOM_REF[clef] + step
        note = Note(LETTERS[diatonic % 7], 0, diatonic // 7)
        self.noteRequested.emit(slot, self.selected_voice, note)
        self.update()
