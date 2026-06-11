"""Music staff widget: renders spelled notes at correct positions (treble,
bass, or grand staff) with accidentals and ledger lines, supports chord
columns with proper accidental lanes, note durations (whole/half/quarter
head styles), an optional time signature with barlines, and click-to-place
note entry for melodic dictation.

Engraving notes
---------------
* Noteheads are tilted ovals (~ -20 degrees), sized so a head fills its
  line/space; whole notes render as wider, untilted, hollow ovals without a
  stem; half notes are hollow with a stem.
* Accidentals are placed from real font metrics: the glyph's tight bounding
  rect is measured and its right edge is set a fixed gap left of the
  notehead, vertically centered on the head (flats get a small per-glyph
  nudge so the bowl, not the stem, sits on the note's line). Within a chord,
  accidentals get their own columns left of the noteheads, closest lane
  nearest the chord (Gould's rule), so they never collide.
* Chords stack vertically in one column; adjacent seconds alternate the
  notehead to the other side of the stem, as engraved.
* Glyphs come from the platform's symbol fonts (Segoe UI Symbol first). A
  bundled SMuFL font (Bravura) was considered and skipped for now: the
  Unicode glyphs render cleanly on Windows and bundling would add an asset
  plus font-loading code for marginal gain. Revisit if cross-platform
  polish demands it.
* Appearance (size, accidental scale/gap, notehead style, labels, highlight)
  comes from the module-level STYLE dict, configured from user settings via
  configure_staff_appearance(); defaults are the recommended out-of-box look.
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPen
from PyQt6.QtWidgets import QWidget

from ...theory.pitch import LETTERS, Note
from .. import theme

# Diatonic index of the bottom staff line per clef.
_BOTTOM_REF = {"treble": Note("E", 0, 4).diatonic_index, "bass": Note("G", 0, 2).diatonic_index}
_ACC_GLYPH = {-2: "\U0001D12B", -1: "♭", 0: "♮", 1: "♯", 2: "\U0001D12A"}
_ACC_ASCII = {-2: "bb", -1: "b", 0: "♮", 1: "#", 2: "x"}
_CLEF_GLYPH = {"treble": "\U0001D11E", "bass": "\U0001D122"}

# Standard key-signature staff positions (steps above bottom line) per clef.
_SHARP_STEPS = {"treble": [8, 5, 9, 6, 3, 7, 4], "bass": [6, 3, 7, 4, 1, 5, 2]}
_FLAT_STEPS = {"treble": [4, 7, 3, 6, 2, 5, 1], "bass": [2, 5, 1, 4, 0, 3, -1]}

# Fonts that actually contain the Unicode music glyphs (clefs live in the
# Musical Symbols block, U+1D100+). Without an explicit list Qt's fallback can
# miss them (offscreen rendering shows .notdef boxes).
_MUSIC_FONT_FAMILIES = ["Segoe UI Symbol", "Noto Music", "Noto Sans Symbols 2",
                        "DejaVu Sans", "FreeSerif"]


def _music_font(pixel_size: int) -> QFont:
    f = QFont()
    f.setFamilies(_MUSIC_FONT_FAMILIES)
    f.setPixelSize(max(8, pixel_size))
    return f


# Vertical nudge per accidental, in line-spacing units (positive = down).
# Metrics center the glyph's tight box on the notehead; the flat glyphs are
# stem-heavy, so they drop a touch to land the bowl on the note's line.
_ACC_NUDGE = {-2: 0.12, -1: 0.12, 0: 0.0, 1: 0.0, 2: 0.0}

# Appearance presets: staff_size setting -> line spacing in px.
SIZE_PRESETS = {"compact": 12, "comfortable": 17, "large": 22}

# Live appearance state, shared by every StaffWidget. configure_staff_appearance
# overwrites it from settings; these defaults ARE the recommended look.
STYLE = {
    "line_spacing": SIZE_PRESETS["comfortable"],
    "acc_scale": 1.0,        # multiplies the base accidental font (ls * 1.7)
    "acc_gap": 1.0,          # multiplies the base gap (ls * 0.35)
    "notehead": "filled",    # filled | outlined | high_contrast
    "labels": "off",         # off | letters | letters_octave
    "line_highlight": True,  # soft band on the active note's line/space
    "paper": "",             # hex override; "" = theme STAFF_PAPER
}


def configure_staff_appearance(settings) -> None:
    """Pull staff appearance out of the settings store into STYLE.

    Tolerates missing/garbage values (falls back to the recommended default
    per key) so a hand-edited settings file can never break rendering.
    """
    def _get(key, default):
        try:
            return settings.get(key, default)
        except Exception:  # noqa: BLE001
            return default

    STYLE["line_spacing"] = SIZE_PRESETS.get(str(_get("staff_size", "comfortable")),
                                             SIZE_PRESETS["comfortable"])
    try:
        STYLE["acc_scale"] = max(0.7, min(1.6, float(_get("staff_accidental_size", 1.0))))
        STYLE["acc_gap"] = max(0.5, min(2.0, float(_get("staff_accidental_gap", 1.0))))
    except (TypeError, ValueError):
        STYLE["acc_scale"], STYLE["acc_gap"] = 1.0, 1.0
    notehead = str(_get("staff_notehead_style", "filled"))
    STYLE["notehead"] = notehead if notehead in ("filled", "outlined", "high_contrast") else "filled"
    labels = str(_get("staff_note_labels", "off"))
    STYLE["labels"] = labels if labels in ("off", "letters", "letters_octave") else "off"
    STYLE["line_highlight"] = bool(_get("staff_line_highlight", True))
    paper = str(_get("staff_paper", ""))
    STYLE["paper"] = paper if len(paper) == 7 and paper.startswith("#") else ""


class StaffWidget(QWidget):
    noteAdded = pyqtSignal(object)   # emits a Note
    noteRemoved = pyqtSignal(int)

    def __init__(self, clef: str = "treble", parent=None) -> None:
        super().__init__(parent)
        self.clef = clef                      # 'treble' | 'bass' | 'grand'
        self.notes: list[Note] = []
        self.ghost_notes: list[Note] = []     # second-color overlay (e.g. answer)
        self.key_sig: Optional[dict] = None
        self.meter: Optional[tuple[int, int]] = None
        self.allow_input = False
        self.input_alter = 0
        self.prefer_sharps = True
        self._ls_override: Optional[int] = None
        self._columns: list[list[Note]] = []
        self._ghost_columns: list[list[Note]] = []
        self._durations: Optional[list[float]] = None
        self.setAccessibleName("Music staff")

    # line_spacing stays assignable (tests/tools may pin a size); unset means
    # "follow the user's staff_size setting".
    @property
    def line_spacing(self) -> int:
        return self._ls_override if self._ls_override else int(STYLE["line_spacing"])

    @line_spacing.setter
    def line_spacing(self, value: int) -> None:
        self._ls_override = int(value) if value else None
        self.updateGeometry()
        self.update()

    # -- public API -------------------------------------------------------
    def set_clef(self, clef: str) -> None:
        self.clef = clef
        self.updateGeometry()
        self.update()

    def set_notes(self, notes, ghost=None) -> None:
        """Sequential single notes (the original API)."""
        self.notes = [self._as_note(n) for n in notes]
        self.ghost_notes = [self._as_note(n) for n in (ghost or [])]
        self._columns = [[n] for n in self.notes]
        self._ghost_columns = [[n] for n in self.ghost_notes]
        self._durations = None
        self._update_description()
        self.update()

    def set_columns(self, columns, *, durations=None, ghost=None) -> None:
        """Chord-capable API: each column is a note or a list of notes
        sounding together; ``durations`` (beats per column) selects whole /
        half / quarter noteheads and, with a meter set, draws barlines."""
        self._columns = [self._as_group(c) for c in columns]
        self._ghost_columns = [self._as_group(c) for c in (ghost or [])]
        self.notes = [n for col in self._columns for n in col]
        self.ghost_notes = [n for col in self._ghost_columns for n in col]
        if durations is not None:
            durations = [float(d) for d in durations]
        self._durations = durations
        self._update_description()
        self.update()

    def clear(self) -> None:
        self.notes = []
        self.ghost_notes = []
        self._columns = []
        self._ghost_columns = []
        self._durations = None
        self.update()

    def set_key_signature(self, key_sig: Optional[dict]) -> None:
        self.key_sig = key_sig
        self.update()

    def set_meter(self, numerator: Optional[int], denominator: int = 4) -> None:
        """Show a time signature (None hides it)."""
        self.meter = (int(numerator), int(denominator)) if numerator else None
        self.update()

    def pop_note(self) -> None:
        if self.notes:
            removed = self.notes.pop()
            self._columns = [[n] for n in self.notes]
            self.noteRemoved.emit(removed.midi)
            self.update()

    def _as_note(self, n) -> Note:
        if isinstance(n, Note):
            return n
        return Note.from_midi(int(n), self.prefer_sharps)

    def _as_group(self, c) -> list[Note]:
        if isinstance(c, (list, tuple)):
            return sorted((self._as_note(n) for n in c), key=lambda n: n.diatonic_index)
        return [self._as_note(c)]

    def _update_description(self) -> None:
        # text alternative for screen readers, covering every call site
        def col_text(col: list[Note]) -> str:
            return "+".join(n.name for n in col)
        desc = "Notes: " + (" ".join(col_text(c) for c in self._columns) or "none")
        if self._ghost_columns:
            desc += ".  Answer: " + " ".join(col_text(c) for c in self._ghost_columns)
        self.setAccessibleDescription(desc)

    # -- geometry helpers -------------------------------------------------
    def minimumSizeHint(self) -> QSize:  # noqa: N802 - Qt override
        ls = self.line_spacing
        rows = 17.5 if self.clef == "grand" else 11.0
        return QSize(320, int(rows * ls))

    def sizeHint(self) -> QSize:  # noqa: N802 - Qt override
        return self.minimumSizeHint()

    def _staff_tops(self) -> list[tuple[str, float]]:
        """Return [(clef, bottom_line_y)] for each staff to draw."""
        ls = self.line_spacing
        if self.clef == "grand":
            # 3 ls of ledger headroom, 3.5 ls between the staves (room for
            # middle-C ledgers and the clef tails)
            top = ls * 3.0
            return [("treble", top + 4 * ls), ("bass", top + 11.5 * ls)]
        return [(self.clef, self.height() / 2 + 2 * ls)]

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
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        # warm "paper" card with rounded corners so the staff sits like a
        # panel instead of a raw white rectangle in the dark layout
        paper = STYLE["paper"] or theme.STAFF_PAPER
        ink = QColor(theme.STAFF_INK)
        p.setBrush(QColor(paper))
        p.setPen(QPen(QColor(theme.BORDER), 1))
        p.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 8, 8)
        ls = self.line_spacing
        left = 12
        right = self.width() - 12
        clef_font = _music_font(int(ls * 6))
        acc_font = self._acc_font()
        line_pen = QPen(ink, max(1.0, ls * 0.07))

        x_start = left + ls * 3.8
        for clef, bottom_y in self._staff_tops():
            p.setPen(line_pen)
            for i in range(5):
                y = bottom_y - i * ls
                p.drawLine(QPointF(left, y), QPointF(right, y))
            # clef glyph
            p.setFont(clef_font)
            p.setPen(ink)
            p.drawText(QPointF(left + 2, bottom_y - (0.5 if clef == "treble" else 1.5) * ls),
                       _CLEF_GLYPH.get(clef, "?"))
            # key signature: metrics-placed glyphs in their own columns,
            # starting clear of the clef
            kx = left + ls * 4.2
            if self.key_sig and self.key_sig.get("count"):
                alter = 1 if self.key_sig["kind"] == "sharp" else -1
                steps_list = (_SHARP_STEPS if alter > 0 else _FLAT_STEPS)[clef]
                for k in range(self.key_sig["count"]):
                    yy = bottom_y - steps_list[k] * (ls / 2)
                    w = self._draw_accidental(p, acc_font, alter, kx, yy, ink, left_edge=True)
                    kx += w + ls * 0.18
            # time signature (extra right margin: the first column's
            # accidental lanes extend left of its noteheads)
            if self.meter:
                kx += ls * 0.4
                kx = self._draw_meter(p, kx, bottom_y, ink) + ls * 1.2
            x_start = max(x_start, kx + ls * 0.8)

        # draw columns left-to-right; ghost (answer) aligns by index with entry
        count = max(1, len(self._columns), len(self._ghost_columns))
        span = right - x_start - 24
        step_x = max(ls * 2.0, min(ls * 5.5, span / count))
        for i, col in enumerate(self._ghost_columns):
            self._draw_column(p, col, x_start + ls * 1.2 + i * step_x, acc_font, True,
                              self._duration_at(i))
        for i, col in enumerate(self._columns):
            self._draw_column(p, col, x_start + ls * 1.2 + i * step_x, acc_font, False,
                              self._duration_at(i))

        # barlines between measures (needs a meter and per-column durations)
        if self.meter and self._durations and self._columns:
            beats_per_bar = self.meter[0] * 4.0 / self.meter[1]
            acc = 0.0
            for i, dur in enumerate(self._durations[:len(self._columns)]):
                acc += dur
                if acc >= beats_per_bar - 1e-6:
                    acc = 0.0
                    bx = x_start + ls * 1.2 + (i + 0.5) * step_x + step_x * 0.25
                    if i == len(self._columns) - 1:
                        bx = min(bx, right - ls * 0.4)
                    p.setPen(QPen(ink, max(1.0, ls * 0.08)))
                    tops = self._staff_tops()
                    y0 = tops[0][1] - 4 * ls
                    y1 = tops[-1][1]
                    p.drawLine(QPointF(bx, y0), QPointF(bx, y1))
        p.end()

    def _duration_at(self, i: int) -> Optional[float]:
        if self._durations and i < len(self._durations):
            return self._durations[i]
        return None

    def _acc_font(self) -> QFont:
        return _music_font(int(self.line_spacing * 1.7 * STYLE["acc_scale"]))

    def _draw_meter(self, p: QPainter, x: float, bottom_y: float, ink: QColor) -> float:
        """Draw the time signature; return the x just past it."""
        num, den = self.meter
        ls = self.line_spacing
        f = QFont()
        f.setPixelSize(int(ls * 2.1))
        f.setBold(True)
        fm = QFontMetricsF(f)
        p.setFont(f)
        p.setPen(ink)
        w = max(fm.horizontalAdvance(str(num)), fm.horizontalAdvance(str(den)))
        # numerator centered in the top half, denominator in the bottom half
        p.drawText(QPointF(x + (w - fm.horizontalAdvance(str(num))) / 2,
                           bottom_y - 2 * ls - ls * 0.25), str(num))
        p.drawText(QPointF(x + (w - fm.horizontalAdvance(str(den))) / 2,
                           bottom_y - ls * 0.25), str(den))
        return x + w

    def _draw_accidental(self, p: QPainter, font: QFont, alter: int,
                         x: float, y: float, color: QColor, *,
                         left_edge: bool = False) -> float:
        """Draw an accidental glyph metrically anchored to (x, y).

        With ``left_edge`` the glyph's left edge lands at x (key signatures);
        otherwise its *right* edge lands at x (note accidentals). The glyph's
        tight bounding box is vertically centered on y, plus a small per-glyph
        nudge. Returns the glyph's drawn width.
        """
        glyph = _ACC_GLYPH[alter]
        fm = QFontMetricsF(font)
        r = fm.tightBoundingRect(glyph)
        if r.width() <= 0:  # missing glyph in fallback font: bail politely
            return 0.0
        bx = (x - r.x()) if left_edge else (x - r.x() - r.width())
        by = y - r.y() - r.height() / 2 + _ACC_NUDGE.get(alter, 0.0) * self.line_spacing
        p.setFont(font)
        p.setPen(color)
        p.drawText(QPointF(bx, by), glyph)
        return r.width()

    def _acc_width(self, font: QFont, alter: int) -> float:
        fm = QFontMetricsF(font)
        return fm.tightBoundingRect(_ACC_GLYPH[alter]).width()

    # -- chord/column drawing ----------------------------------------------
    def _draw_column(self, p: QPainter, col: list[Note], x: float, acc_font: QFont,
                     ghost: bool, duration: Optional[float]) -> None:
        if not col:
            return
        if self.clef == "grand":
            staves = dict(self._staff_tops())
            treble = [n for n in col if n.midi >= 60]
            bass = [n for n in col if n.midi < 60]
            if treble:
                self._draw_chord(p, treble, x, "treble", staves["treble"], acc_font,
                                 ghost, duration)
            if bass:
                self._draw_chord(p, bass, x, "bass", staves["bass"], acc_font,
                                 ghost, duration)
        else:
            clef, bottom_y = self._staff_tops()[0]
            self._draw_chord(p, col, x, clef, bottom_y, acc_font, ghost, duration)

    def _draw_chord(self, p: QPainter, notes: list[Note], x: float, clef: str,
                    bottom_y: float, acc_font: QFont, ghost: bool,
                    duration: Optional[float]) -> None:
        """One chord (1..n notes) at column x on a single staff."""
        ls = self.line_spacing
        ink = QColor(theme.STAFF_INK)
        # ghost (answer) notes need >=3:1 against the paper (WCAG 1.4.11)
        color = QColor("#8a8a8a") if ghost else ink
        whole = duration is not None and duration >= 4.0
        half = duration is not None and 2.0 <= duration < 4.0
        rw, rh = (ls * 1.55, ls * 0.92) if whole else (ls * 1.30, ls * 0.86)

        notes = sorted(notes, key=lambda n: n.diatonic_index)
        steps_list = [n.diatonic_index - _BOTTOM_REF[clef] for n in notes]
        avg_steps = sum(steps_list) / len(steps_list)
        stem_up = avg_steps < 4
        stem_x = x + rw / 2 - ls * 0.06 if stem_up else x - rw / 2 + ls * 0.06

        # seconds: alternate offending heads to the other side of the stem
        offsets = [0.0] * len(notes)
        for i in range(1, len(notes)):
            if steps_list[i] - steps_list[i - 1] <= 1 and offsets[i - 1] == 0.0:
                offsets[i] = rw * 0.92 if stem_up else -rw * 0.92

        # highlight bands first (under everything)
        if STYLE["line_highlight"] and not ghost and not whole:
            band = QColor(theme.ACCENT)
            band.setAlpha(46)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(band)
            for n, off in zip(notes, offsets):
                y = self._y_for(n, clef, bottom_y)
                p.drawRoundedRect(QRectF(x + off - ls * 1.6, y - ls * 0.48,
                                         ls * 3.2, ls * 0.96), ls * 0.3, ls * 0.3)

        # ledger lines (cover offset heads too)
        p.setPen(QPen(color, max(1.0, ls * 0.08)))
        ledger_span = rw * 0.78 + max(abs(o) for o in offsets) if offsets else rw * 0.78
        drawn_ledgers = set()
        for n in notes:
            steps = n.diatonic_index - _BOTTOM_REF[clef]
            if steps < 0:
                k = -2
                while k >= steps:
                    if k not in drawn_ledgers:
                        ly = bottom_y - k * (ls / 2)
                        p.drawLine(QPointF(x - ledger_span, ly), QPointF(x + ledger_span, ly))
                        drawn_ledgers.add(k)
                    k -= 2
            elif steps > 8:
                k = 10
                while k <= steps:
                    if k not in drawn_ledgers:
                        ly = bottom_y - k * (ls / 2)
                        p.drawLine(QPointF(x - ledger_span, ly), QPointF(x + ledger_span, ly))
                        drawn_ledgers.add(k)
                    k += 2

        # noteheads
        paper_c = QColor(STYLE["paper"] or theme.STAFF_PAPER)
        style = STYLE["notehead"]
        hollow = whole or half or style == "outlined"
        for n, off in zip(notes, offsets):
            y = self._y_for(n, clef, bottom_y)
            p.save()
            p.translate(x + off, y)
            if not whole:
                p.rotate(-20)
            if hollow:
                p.setBrush(paper_c)
                p.setPen(QPen(color, max(1.6, ls * (0.16 if whole else 0.13))))
            elif style == "high_contrast" and not ghost:
                # halo ring in the paper color so heads pop off staff lines
                p.setBrush(color)
                p.setPen(QPen(paper_c, max(2.0, ls * 0.16)))
            else:
                p.setBrush(color)
                p.setPen(QPen(color, 1))
            p.drawEllipse(QRectF(-rw / 2, -rh / 2, rw, rh))
            p.restore()

        # stem: one per chord, spanning lowest to highest head, whole notes none
        if not whole:
            p.setPen(QPen(color, max(1.2, ls * 0.09)))
            y_low = self._y_for(notes[0], clef, bottom_y)
            y_high = self._y_for(notes[-1], clef, bottom_y)
            stem_len = ls * 3.2
            if stem_up:
                p.drawLine(QPointF(stem_x, y_low - ls * 0.12),
                           QPointF(stem_x, y_high - stem_len))
            else:
                p.drawLine(QPointF(stem_x, y_high + ls * 0.12),
                           QPointF(stem_x, y_low + stem_len))

        # accidentals in lanes left of the chord (closest lane nearest the
        # heads; a new lane opens when two accidentals would collide vertically)
        accs = [(self._y_for(n, clef, bottom_y), n.alter) for n in notes if n.alter != 0]
        if accs:
            accs.sort(key=lambda t: t[0])            # top first
            gap = ls * 0.35 * STYLE["acc_gap"]
            min_clear = ls * 1.6                      # vertical clearance per lane
            lane_last_y: list[float] = []
            lane_w = max(self._acc_width(acc_font, a) for _, a in accs) + ls * 0.12
            head_left = x - rw / 2 - max((-o for o in offsets if o < 0), default=0.0)
            for y, alter in accs:
                lane = 0
                while lane < len(lane_last_y) and y - lane_last_y[lane] < min_clear:
                    lane += 1
                if lane == len(lane_last_y):
                    lane_last_y.append(y)
                else:
                    lane_last_y[lane] = y
                ax = head_left - gap - lane * lane_w
                self._draw_accidental(p, acc_font, alter, ax, y, color)

        # optional note-name labels (single notes only: chords would clutter)
        if STYLE["labels"] != "off" and not ghost and len(notes) == 1:
            n = notes[0]
            y = self._y_for(n, clef, bottom_y)
            label = n.letter + (_ACC_ASCII[n.alter] if n.alter else "")
            if STYLE["labels"] == "letters_octave":
                label += str(n.octave)
            lf = QFont()
            lf.setPixelSize(max(9, int(ls * 0.72)))
            lf.setBold(True)
            fm = QFontMetricsF(lf)
            steps = n.diatonic_index - _BOTTOM_REF[clef]
            ly = y + (ls * 3.2 + ls * 0.9 if steps >= 4 and not whole else ls * 1.25)
            p.setFont(lf)
            p.setPen(ink)
            p.drawText(QPointF(x - fm.horizontalAdvance(label) / 2, ly), label)

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
        self._columns = [[n] for n in self.notes]
        self.noteAdded.emit(note)
        self.update()
