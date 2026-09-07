"""Four-Part Writing Lab and Fall 2026 course companion."""

from __future__ import annotations

import random
import threading
from pathlib import Path

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, QObject, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QAbstractItemView, QButtonGroup, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QDoubleSpinBox, QFileDialog, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QPlainTextEdit, QPushButton, QScrollArea, QSpinBox, QTabWidget, QTableView,
    QTableWidget, QTableWidgetItem, QTextBrowser, QVBoxLayout, QWidget,
)

from ...curriculum.fall_2026 import FALL_2026_COURSES, UTC_SUPPORT
from ...errors import guard
from ...theory.part_writing.diagnostics import check_solution, explain, summarize
from ...theory.part_writing.export import export_musicxml
from ...theory.part_writing.generator import PracticeType, generate_practice
from ...theory.part_writing.models import (
    CadenceType, ChordFactor, Clef, HarmonyConstraint, HarmonySlot, Layout,
    PartWritingProblem, PitchConstraint, RuleSeverity, SolveResult,
    SolverOptions, Voice, VOICE_ORDER, Voicing,
)
from ...theory.part_writing.profiles import (
    PROFILES, RuleProfile, custom_profile, profile_for,
)
from ...theory.part_writing.serialization import (
    SerializationError, load_problem, problem_from_dict, problem_to_dict,
    profile_to_dict, save_problem,
)
from ...theory.part_writing.solver import solve
from ...theory.part_writing.solver import auto_correct
from ...theory.pitch import Note
from .. import theme
from ..widgets import PianoWidget, SatbStaffWidget


_ROWS = ("Roman numeral", "Figured bass", "Chord symbol",
         "Soprano", "Alto", "Tenor", "Bass", "Duration")
_VOICE_ROWS = {
    3: Voice.SOPRANO, 4: Voice.ALTO, 5: Voice.TENOR, 6: Voice.BASS,
}


def parse_assignment(text: str, template: PartWritingProblem) -> PartWritingProblem:
    """Parse aligned, pipe-separated clues atomically; every supplied note is a given."""
    import copy
    rows = {}
    aliases = {"s": "soprano", "a": "alto", "t": "tenor", "b": "bass",
               "roman": "roman", "chords": "chords", "figures": "figures",
               "duration": "duration", **{v.value: v.value for v in VOICE_ORDER}}
    for line in text.splitlines():
        if not line.strip():
            continue
        label, sep, values = line.partition(":")
        key = aliases.get(label.strip().lower())
        if not sep or not key or key in rows:
            raise ValueError("Use each row once: Roman, Chords, Figures, S, A, T, B, Duration.")
        rows[key] = [v.strip() for v in values.split("|")]
    lengths = {len(row) for row in rows.values()}
    if len(lengths) != 1:
        raise ValueError("Every supplied row must have the same number of | separated cells; use ? for unknowns.")
    result = copy.deepcopy(template)
    result.slots = [HarmonySlot() for _ in range(next(iter(lengths)))]
    for key, cells in rows.items():
        for index, value in enumerate(cells):
            if value in ("", "?", "-"):
                continue
            slot = result.slots[index]
            if key in {"roman", "chords", "figures"}:
                setattr(slot.harmony, {"roman": "roman_numeral", "chords": "chord_symbol",
                                      "figures": "figured_bass"}[key], value)
            elif key == "duration":
                import math
                slot.duration = float(value)
                if not math.isfinite(slot.duration) or slot.duration <= 0:
                    raise ValueError("Durations must be finite, positive beats.")
            else:
                constraint = slot.voice(Voice(key))
                constraint.pitch = _parse_pitch_constraint(value)
                constraint.locked = True
    return result

_CUSTOM_RULE_LABELS = {
    "Enforce voice ranges": "VL_RANGE",
    "Forbid voice crossing": "VL_VOICE_CROSSING",
    "Forbid parallel unisons": "VL_PARALLEL_P1",
    "Forbid parallel fifths": "VL_PARALLEL_P5",
    "Forbid parallel octaves": "VL_PARALLEL_P8",
    "Forbid parallel fourths": "VL_PARALLEL_P4",
    "Forbid hidden fifths in outer voices": "VL_HIDDEN_P5",
    "Forbid hidden octaves in outer voices": "VL_HIDDEN_P8",
    "Require leading-tone resolution": "TENDENCY_LEADING_TONE",
    "Require chordal-seventh resolution": "TENDENCY_CHORDAL_SEVENTH",
    "Forbid doubled leading tone": "CHORD_DOUBLED_LEADING_TONE",
    "Enforce upper-voice spacing": "VL_UPPER_SPACING",
    "Enforce voice overlap rules": "VL_VOICE_OVERLAP",
    "Require exact chord membership": "CHORD_MEMBERSHIP",
    "Require valid inversion": "CHORD_INVERSION",
    "Honor explicit note constraints": "CONSTRAINT_REQUIRED",
    "Honor required doublings": "CHORD_REQUIRED_DOUBLING",
    "Forbid doubled chordal seventh": "CHORD_DOUBLED_SEVENTH",
    "Treat anti-parallel perfect displacement as parallel": "VL_ANTIPARALLEL_PERFECT",
    "Enforce augmented-sixth resolution": "TENDENCY_AUGMENTED_SIXTH",
    "Enforce cadential six-four resolution": "CADENCE_CADENTIAL_64",
    "Forbid augmented melodic intervals": "MELODY_AUGMENTED_INTERVAL",
    "Forbid melodic sevenths": "MELODY_SEVENTH",
    "Limit large melodic leaps": "MELODY_LARGE_LEAP",
    "Enforce melodic leap recovery": "MELODY_LEAP_RECOVERY",
    "Limit consecutive leaps": "MELODY_CONSECUTIVE_LEAPS",
    "Require complete triads": "CHORD_COMPLETENESS",
    "Enforce diminished-fifth expansion rule": "VL_UNEQUAL_FIFTH",
    "Forbid voice unisons": "VL_FORBIDDEN_UNISON",
    "Strict cadential soprano resolution": "CADENCE_REQUIREMENT",
}


def _new_problem() -> PartWritingProblem:
    return PartWritingProblem(slots=[
        HarmonySlot(HarmonyConstraint(roman_numeral=label))
        for label in ("I", "IV", "V", "I")
    ], cadence=CadenceType.PERFECT_AUTHENTIC)


def _pitch_text(constraint: PitchConstraint) -> str:
    if constraint.exact is not None:
        return constraint.exact.name
    if constraint.pitch_class is not None:
        return constraint.pitch_class.name_no_octave
    if constraint.scale_degree is not None:
        return f"scale degree {constraint.scale_degree}"
    if constraint.chord_factor is not None:
        return constraint.chord_factor.value
    if constraint.allowed_pitches:
        return " / ".join(note.name for note in constraint.allowed_pitches)
    return ""


def _parse_pitch_constraint(text: str) -> PitchConstraint:
    value = text.strip().replace("♯", "#").replace("♭", "b")
    if not value:
        return PitchConstraint()
    lower = value.lower()
    for factor in ChordFactor:
        if lower == factor.value:
            return PitchConstraint(chord_factor=factor)
    if lower.startswith("scale degree"):
        degree = int(lower.split()[-1])
        if not 1 <= degree <= 7:
            raise ValueError("Scale degree must be 1 through 7")
        return PitchConstraint(scale_degree=degree)
    if lower.startswith("^"):
        degree = int(lower[1:])
        if not 1 <= degree <= 7:
            raise ValueError("Scale degree must be 1 through 7")
        return PitchConstraint(scale_degree=degree)
    has_octave = value[-1:].isdigit() or (len(value) >= 2 and value[-2] == "-" and value[-1].isdigit())
    note = Note.parse(value)
    return PitchConstraint(exact=note) if has_octave else PitchConstraint(pitch_class=note)


class PartWritingTableModel(QAbstractTableModel):
    changed = pyqtSignal()

    def __init__(self, problem: PartWritingProblem, parent=None) -> None:
        super().__init__(parent)
        self.problem = problem

    def rowCount(self, _parent=QModelIndex()) -> int:  # noqa: N802
        return len(_ROWS)

    def columnCount(self, _parent=QModelIndex()) -> int:  # noqa: N802
        return len(self.problem.slots)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):  # noqa: N802
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        return _ROWS[section] if orientation == Qt.Orientation.Vertical else str(section + 1)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        slot = self.problem.slots[index.column()]
        row = index.row()
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            if row == 0:
                value = slot.harmony.roman_numeral or ""
            elif row == 1:
                value = slot.harmony.figured_bass or ""
            elif row == 2:
                value = slot.harmony.chord_symbol or ""
            elif row in _VOICE_ROWS:
                constraint = slot.voice(_VOICE_ROWS[row])
                value = _pitch_text(constraint.pitch)
                if role == Qt.ItemDataRole.DisplayRole and constraint.locked and value:
                    value = f"LOCK {value}"
            else:
                value = f"{slot.duration:g}"
            return value
        if role == Qt.ItemDataRole.BackgroundRole and row in _VOICE_ROWS:
            constraint = slot.voice(_VOICE_ROWS[row])
            if constraint.locked:
                color = QColor(theme.ACCENT)
                color.setAlpha(45)
                return color
        if role == Qt.ItemDataRole.ToolTipRole:
            if row in _VOICE_ROWS:
                constraint = slot.voice(_VOICE_ROWS[row])
                state = "Locked; the solver cannot change this requirement." if constraint.locked else "Unlocked constraint."
                return f"{state} Accepts C4, F#4, Bb, scale degree 3, root, third, fifth, or seventh."
            return "Leave blank when unknown."
        if role == Qt.ItemDataRole.AccessibleTextRole:
            value = self.data(index, Qt.ItemDataRole.DisplayRole) or "blank"
            return f"Slot {index.column() + 1}, {_ROWS[row]}, {value}"
        return None

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return (Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsEditable)

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):  # noqa: N802
        if role != Qt.ItemDataRole.EditRole or not index.isValid():
            return False
        text = str(value).strip()
        if text.upper().startswith("LOCK "):
            text = text[5:].strip()
        slot = self.problem.slots[index.column()]
        row = index.row()
        try:
            if row == 0:
                slot.harmony.roman_numeral = text or None
            elif row == 1:
                slot.harmony.figured_bass = text or None
            elif row == 2:
                slot.harmony.chord_symbol = text or None
            elif row in _VOICE_ROWS:
                slot.voice(_VOICE_ROWS[row]).pitch = _parse_pitch_constraint(text)
            else:
                duration = float(text)
                if duration <= 0:
                    raise ValueError("Duration must be positive")
                slot.duration = duration
        except (ValueError, TypeError):
            return False
        self.dataChanged.emit(index, index)
        self.changed.emit()
        return True

    def replace_problem(self, problem: PartWritingProblem) -> None:
        self.beginResetModel()
        self.problem = problem
        self.endResetModel()
        self.changed.emit()

    def insert_slot(self, column: int | None = None, slot: HarmonySlot | None = None) -> None:
        column = len(self.problem.slots) if column is None else max(0, min(column, len(self.problem.slots)))
        self.beginInsertColumns(QModelIndex(), column, column)
        self.problem.slots.insert(column, slot or HarmonySlot())
        self.endInsertColumns()
        self.changed.emit()

    def remove_slot(self, column: int) -> None:
        if len(self.problem.slots) <= 1 or not 0 <= column < len(self.problem.slots):
            return
        self.beginRemoveColumns(QModelIndex(), column, column)
        self.problem.slots.pop(column)
        self.endRemoveColumns()
        self.changed.emit()


class _SolveWorker(QObject):
    completed = pyqtSignal(object)
    progress = pyqtSignal(int, int)

    def __init__(self, problem: PartWritingProblem, profile: RuleProfile,
                 options: SolverOptions) -> None:
        super().__init__()
        self.problem = problem
        self.profile = profile
        self.options = options

    def run(self) -> None:
        try:
            self.options.progress_callback = self.progress.emit
            self.completed.emit(solve(self.problem, self.profile, self.options))
        except Exception as exc:  # noqa: BLE001 - worker boundary must surface safely
            self.completed.emit(exc)


class RuleProfileDialog(QDialog):
    def __init__(self, profile: RuleProfile, parent=None) -> None:
        super().__init__(parent)
        from ...theory.part_writing.models import RuleCode
        self.profile = custom_profile(profile)
        self.setWindowTitle("Custom part-writing profile")
        self.resize(720, 650)
        layout = QVBoxLayout(self)
        intro = QLabel(
            "Set each disputed rule to hard, conditional, soft, or disabled. "
            "Custom settings remain local to this app profile.")
        intro.setWordWrap(True); layout.addWidget(intro)
        self.rules = QTableWidget(len(_CUSTOM_RULE_LABELS), 2)
        self.rules.setHorizontalHeaderLabels(("Rule", "Severity"))
        self.rules.setAccessibleName("Custom rule severities")
        self._rule_boxes = {}
        for row, (label, raw_code) in enumerate(_CUSTOM_RULE_LABELS.items()):
            code = RuleCode(raw_code)
            self.rules.setItem(row, 0, QTableWidgetItem(label))
            box = QComboBox()
            for severity in (RuleSeverity.HARD_ERROR, RuleSeverity.CONDITIONAL_ERROR,
                             RuleSeverity.SOFT_PENALTY, RuleSeverity.DISABLED):
                box.addItem(severity.value.replace("-", " ").title(), severity.value)
            index = box.findData(self.profile.severity(code).value)
            box.setCurrentIndex(max(0, index))
            self.rules.setCellWidget(row, 1, box); self._rule_boxes[code] = box
        self.rules.resizeColumnsToContents(); layout.addWidget(self.rules, 1)
        range_grid = QGridLayout(); range_grid.addWidget(QLabel("Voice range"), 0, 0)
        range_grid.addWidget(QLabel("Minimum"), 0, 1); range_grid.addWidget(QLabel("Maximum"), 0, 2)
        self._range_edits = {}
        for row, voice in enumerate(VOICE_ORDER, start=1):
            allowed = self.profile.voice_ranges[voice]
            minimum = QLineEdit(allowed.minimum.name); maximum = QLineEdit(allowed.maximum.name)
            minimum.setAccessibleName(f"{voice.value} minimum pitch")
            maximum.setAccessibleName(f"{voice.value} maximum pitch")
            range_grid.addWidget(QLabel(voice.value.title()), row, 0)
            range_grid.addWidget(minimum, row, 1); range_grid.addWidget(maximum, row, 2)
            self._range_edits[voice] = (minimum, maximum)
        layout.addLayout(range_grid)
        self.weights = QTableWidget(len(self.profile.weights), 2)
        self.weights.setHorizontalHeaderLabels(("Soft preference", "Weight"))
        self.weights.setAccessibleName("Soft preference weights")
        self._weight_boxes = {}
        for row, (name, value) in enumerate(sorted(self.profile.weights.items())):
            self.weights.setItem(row, 0, QTableWidgetItem(name.replace("_", " ").title()))
            box = QDoubleSpinBox(); box.setRange(-20.0, 20.0); box.setDecimals(2); box.setValue(value)
            self.weights.setCellWidget(row, 1, box); self._weight_boxes[name] = box
        self.weights.setMaximumHeight(190); self.weights.resizeColumnsToContents(); layout.addWidget(self.weights)
        self.complete_triads = QCheckBox("Require complete triads")
        self.complete_triads.setChecked(self.profile.require_complete_triads)
        self.incomplete_v7 = QCheckBox("Allow incomplete root-position V7")
        self.incomplete_v7.setChecked(self.profile.allow_incomplete_dominant_seventh)
        self.unequal = QCheckBox("Permit unequal-fifth exceptions")
        self.unequal.setChecked(self.profile.permit_unequal_fifths)
        self.unisons = QCheckBox("Permit voice unisons")
        self.unisons.setChecked(self.profile.permit_voice_unisons)
        self.compounds = QCheckBox("Treat compound fifths/octaves as parallels")
        self.compounds.setChecked(self.profile.treat_compound_perfects)
        options = QHBoxLayout()
        for widget in (self.complete_triads, self.incomplete_v7, self.unequal,
                       self.unisons, self.compounds):
            options.addWidget(widget)
        layout.addLayout(options)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save
                                   | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._accept_profile); buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @guard("RuleProfileDialog._accept_profile")
    def _accept_profile(self) -> None:
        from ...theory.part_writing.models import VoiceRange
        for code, box in self._rule_boxes.items():
            self.profile.severities[code] = RuleSeverity(box.currentData())
        for voice, (minimum, maximum) in self._range_edits.items():
            low, high = Note.parse(minimum.text()), Note.parse(maximum.text())
            if low.midi > high.midi:
                self.setWindowTitle(f"Invalid range for {voice.value}")
                return
            self.profile.voice_ranges[voice] = VoiceRange(low, high)
        self.profile.weights = {name: box.value() for name, box in self._weight_boxes.items()}
        self.profile.require_complete_triads = self.complete_triads.isChecked()
        self.profile.allow_incomplete_dominant_seventh = self.incomplete_v7.isChecked()
        self.profile.permit_unequal_fifths = self.unequal.isChecked()
        self.profile.permit_voice_unisons = self.unisons.isChecked()
        self.profile.treat_compound_perfects = self.compounds.isChecked()
        self.accept()


class SlotConstraintDialog(QDialog):
    """Edit constraints that do not fit naturally into the compact grid."""

    def __init__(self, slot: HarmonySlot, slot_index: int, parent=None) -> None:
        super().__init__(parent)
        self.slot = slot
        self.setWindowTitle(f"Slot {slot_index + 1} constraints")
        self.setMinimumWidth(560)
        layout = QVBoxLayout(self)
        intro = QLabel(
            "These are hard constraints. The solver will either honor every one or "
            "return an explanation; blank fields remain unknown.")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        grid = QGridLayout()
        self.inversion = QComboBox()
        for label, value in (("Unspecified", None), ("Root position", 0),
                             ("First inversion", 1), ("Second inversion", 2),
                             ("Third inversion", 3)):
            self.inversion.addItem(label, value)
        current = self.inversion.findData(slot.harmony.inversion)
        self.inversion.setCurrentIndex(max(0, current))
        self.inversion.setAccessibleName("Required inversion")
        self.bass = QLineEdit(slot.harmony.exact_bass_pitch.name
                              if slot.harmony.exact_bass_pitch else "")
        self.bass.setPlaceholderText("Example: G2")
        self.bass.setAccessibleName("Required exact bass pitch")
        self.doubling = QComboBox()
        self.doubling.addItem("Unspecified", None)
        for factor in ChordFactor:
            self.doubling.addItem(factor.value.title(), factor.value)
        if slot.harmony.required_doubling:
            self.doubling.setCurrentIndex(
                self.doubling.findData(slot.harmony.required_doubling.value))
        self.doubling.setAccessibleName("Required doubled chord factor")
        self.required_tones = QLineEdit(", ".join(slot.harmony.required_chord_tones))
        self.forbidden_tones = QLineEdit(", ".join(slot.harmony.forbidden_chord_tones))
        self.allowed_harmonies = QLineEdit(", ".join(slot.harmony.allowed_harmonies))
        self.forbidden_harmonies = QLineEdit(", ".join(slot.harmony.forbidden_harmonies))
        fields = (
            ("Required inversion", self.inversion),
            ("Required bass", self.bass),
            ("Required doubling", self.doubling),
            ("Required tones", self.required_tones),
            ("Forbidden tones", self.forbidden_tones),
            ("Allowed harmonies", self.allowed_harmonies),
            ("Forbidden harmonies", self.forbidden_harmonies),
        )
        for row, (label, widget) in enumerate(fields):
            grid.addWidget(QLabel(label), row, 0)
            grid.addWidget(widget, row, 1)
        layout.addLayout(grid)
        layout.addWidget(QLabel("Required display clef and optional source label by voice"))
        clef_grid = QGridLayout()
        clef_grid.addWidget(QLabel("Voice"), 0, 0)
        clef_grid.addWidget(QLabel("Clef"), 0, 1)
        clef_grid.addWidget(QLabel("Source label"), 0, 2)
        self.clef_boxes = {}
        self.source_edits = {}
        for row, voice in enumerate(VOICE_ORDER, start=1):
            box = QComboBox(); box.addItem("Default", None)
            for clef in Clef:
                box.addItem(clef.value.title(), clef.value)
            current_clef = slot.voice(voice).clef
            if current_clef:
                box.setCurrentIndex(box.findData(current_clef.value))
            box.setAccessibleName(f"Required {voice.value} clef")
            source = QLineEdit(slot.voice(voice).source_label)
            source.setAccessibleName(f"{voice.value} source label")
            self.clef_boxes[voice] = box; self.source_edits[voice] = source
            clef_grid.addWidget(QLabel(voice.value.title()), row, 0)
            clef_grid.addWidget(box, row, 1); clef_grid.addWidget(source, row, 2)
        layout.addLayout(clef_grid)
        self.error = QLabel("")
        self.error.setObjectName("Danger")
        self.error.setAccessibleName("Constraint validation message")
        layout.addWidget(self.error)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._accept_constraints)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @staticmethod
    def _csv(edit: QLineEdit) -> tuple[str, ...]:
        return tuple(item.strip() for item in edit.text().split(",") if item.strip())

    @guard("SlotConstraintDialog._accept_constraints")
    def _accept_constraints(self) -> None:
        try:
            bass = Note.parse(self.bass.text().strip()) if self.bass.text().strip() else None
        except ValueError as exc:
            self.error.setText(f"Bass pitch: {exc}")
            return
        harmony = self.slot.harmony
        harmony.inversion = self.inversion.currentData()
        harmony.exact_bass_pitch = bass
        value = self.doubling.currentData()
        harmony.required_doubling = ChordFactor(value) if value else None
        harmony.required_chord_tones = self._csv(self.required_tones)
        harmony.forbidden_chord_tones = self._csv(self.forbidden_tones)
        harmony.allowed_harmonies = self._csv(self.allowed_harmonies)
        harmony.forbidden_harmonies = self._csv(self.forbidden_harmonies)
        for voice in VOICE_ORDER:
            value = self.clef_boxes[voice].currentData()
            self.slot.voice(voice).clef = Clef(value) if value else None
            self.slot.voice(voice).source_label = self.source_edits[voice].text().strip()
        self.accept()


class CourseGuideWidget(QWidget):
    def __init__(self, ctx, parent=None) -> None:
        super().__init__(parent)
        self.ctx = ctx
        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        header.addWidget(QLabel("Course:"))
        self.course = QComboBox()
        self.course.setAccessibleName("Fall 2026 course")
        for item in FALL_2026_COURSES:
            self.course.addItem(f"{item.code} · {item.title}", item.code)
        self.course.currentIndexChanged.connect(self._refresh)
        header.addWidget(self.course)
        header.addStretch(1)
        layout.addLayout(header)
        self.content = QTextBrowser()
        self.content.setOpenExternalLinks(False)
        self.content.setAccessibleName("Course outcomes and semester plan")
        layout.addWidget(self.content, 1)
        self.milestones = QListWidget()
        self.milestones.setAccessibleName("Course milestones; press Space to mark complete")
        self.milestones.itemChanged.connect(self._save_checks)
        layout.addWidget(QLabel("Milestones"))
        layout.addWidget(self.milestones)
        self._refresh()

    @guard("CourseGuideWidget._refresh")
    def _refresh(self) -> None:
        guide = FALL_2026_COURSES[max(0, self.course.currentIndex())]
        outcomes = "".join(f"<li>{item}</li>" for item in guide.outcomes)
        materials = "".join(f"<li>{item}</li>" for item in guide.materials)
        grading = "".join(f"<li>{name}: {weight}%</li>" for name, weight in guide.assessments)
        policies = "".join(f"<li>{item}</li>" for item in guide.policies)
        technology = "".join(f"<li>{item}</li>" for item in guide.technology)
        grading_notes = "".join(f"<li>{item}</li>" for item in guide.grading_notes)
        support = "".join(f"<li>{item}</li>" for item in UTC_SUPPORT)
        units = "".join(
            f"<h3>{unit.title} · {unit.dates}</h3><ul>"
            + "".join(f"<li>{topic}</li>" for topic in unit.topics)
            + "</ul><p><b>Practice:</b> " + "; ".join(unit.practice) + "</p>"
            for unit in guide.units
        )
        self.content.setHtml(
            f"<h2>{guide.code}: {guide.title}</h2>"
            f"<p><b>Instructor:</b> {guide.instructor}<br><b>Contact/office:</b> {guide.contact}<br>"
            f"<b>Meeting:</b> {guide.meeting}<br>"
            f"<b>CRN/Credits:</b> {guide.crn} / {guide.credits}</p>"
            f"<p>{guide.description}</p><p><b>Prerequisites:</b> {guide.prerequisites}</p>"
            f"<h3>Materials</h3><ul>{materials}</ul><h3>Learning outcomes</h3><ul>{outcomes}</ul>"
            f"<h3>Assessment weights</h3><ul>{grading}</ul><h3>Grading details</h3>"
            f"<ul>{grading_notes}</ul><h3>Course policies to remember</h3><ul>{policies}</ul>"
            f"<h3>Technology and assignment systems</h3><ul>{technology}</ul>"
            f"<h2>Tentative semester units</h2>{units}<h2>UTC support and institutional reminders</h2>"
            f"<ul>{support}</ul><p><i>Course requirements and dates can change. Canvas and direct "
            "instructor communication are the live sources of truth.</i></p>"
        )
        self.milestones.blockSignals(True)
        self.milestones.clear()
        checked = set(self.ctx.db.kv_get(f"fall2026.completed.{guide.code}", []))
        for milestone in guide.milestones:
            text = f"{milestone.date} · {milestone.title}"
            if milestone.preparation:
                text += " — " + ", ".join(milestone.preparation)
            from PyQt6.QtWidgets import QListWidgetItem
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, milestone.date + "|" + milestone.title)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if item.data(Qt.ItemDataRole.UserRole) in checked
                               else Qt.CheckState.Unchecked)
            self.milestones.addItem(item)
        self.milestones.blockSignals(False)

    @guard("CourseGuideWidget._save_checks")
    def _save_checks(self) -> None:
        guide = FALL_2026_COURSES[max(0, self.course.currentIndex())]
        checked = [self.milestones.item(i).data(Qt.ItemDataRole.UserRole)
                   for i in range(self.milestones.count())
                   if self.milestones.item(i).checkState() == Qt.CheckState.Checked]
        self.ctx.db.kv_set(f"fall2026.completed.{guide.code}", checked)


class PartWritingScreen(QWidget):
    def __init__(self, ctx, parent=None) -> None:
        super().__init__(parent)
        self.ctx = ctx
        self.problem = self._restore_problem()
        self.profile = profile_for(self.problem.profile_id)
        self.solutions = []
        self.solution_index = 0
        self.practice = None
        self._thread: QThread | None = None
        self._worker: _SolveWorker | None = None
        self._cancel: threading.Event | None = None
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        kicker = QLabel("PART WRITING STUDIO")
        kicker.setObjectName("Kicker")
        root.addWidget(kicker)
        title = QLabel("Make room for harmony.")
        title.setObjectName("H1")
        root.addWidget(title)
        subtitle = QLabel("Write a voice. Explore the possibilities. Understand every resolution.")
        subtitle.setObjectName("Subtle")
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)
        self.tabs = QTabWidget()
        self.tabs.setAccessibleName("Part writing and semester guide")
        self.tabs.addTab(self._build_lab(), "Part Writing")
        self.tabs.addTab(CourseGuideWidget(ctx), "Fall 2026 Guide")
        roadmap = QTextBrowser()
        from ...curriculum.lessons import LESSONS
        roadmap.setHtml("<h2>Musicianship III → IV → post-tonal study</h2>"
                        "<p>A practice sequence; your instructor's syllabus determines course requirements. "
                        "Open these named skills in Learn for lessons and graded drills.</p>" +
                        "".join("<h3>" + pages[0].title + "</h3><p>" + pages[-1].body + "</p>"
                                for sid, pages in LESSONS.items() if sid.startswith("tonal.")))
        self.tabs.addTab(roadmap, "Musicianship III–IV")
        root.addWidget(self.tabs, 1)
        self._connect_model()
        self._load_controls_from_problem()
        self._refresh_preview()

    def _build_lab(self) -> QWidget:
        host = QWidget()
        layout = QVBoxLayout(host)
        toolbar = QGridLayout()
        self.mode_box = QComboBox()
        self.mode_box.setAccessibleName("Lab mode")
        self.mode_box.addItems(("Create Practice", "Solve", "Check and Explain"))
        self.key_box = QComboBox(); self.key_box.setEditable(True)
        self.key_box.addItems(("C", "G", "D", "A", "E", "F", "Bb", "Eb", "Ab"))
        self.key_box.setAccessibleName("Key tonic")
        self.tonality_box = QComboBox(); self.tonality_box.addItems(("major", "minor"))
        self.tonality_box.setAccessibleName("Key mode")
        self.meter_box = QComboBox(); self.meter_box.addItems(("4/4", "3/4", "6/8", "2/4"))
        self.meter_box.setAccessibleName("Meter")
        self.profile_box = QComboBox()
        for profile in PROFILES.values():
            self.profile_box.addItem(profile.name, profile.id)
        self.profile_box.addItem("Custom", "custom")
        self.profile_box.setAccessibleName("Voice-leading rule profile")
        self.layout_box = QComboBox()
        for value, label in ((Layout.CHORALE, "Chorale"), (Layout.PIANO, "Piano-style"),
                             (Layout.OPEN_SCORE, "Open score")):
            self.layout_box.addItem(label, value.value)
        self.layout_box.setAccessibleName("Score layout")
        self.cadence_box = QComboBox(); self.cadence_box.addItem("No cadence", "")
        for cadence in CadenceType:
            self.cadence_box.addItem(cadence.value.replace("-", " ").title(), cadence.value)
        self.cadence_box.setAccessibleName("Required cadence")
        self.top_k = QSpinBox(); self.top_k.setRange(1, 20); self.top_k.setValue(5)
        self.top_k.setAccessibleName("Number of solutions")
        for column, (label, widget) in enumerate((
            ("Key", self.key_box), ("Tonality", self.tonality_box),
            ("Meter", self.meter_box), ("Rules", self.profile_box), ("Layout", self.layout_box),
        )):
            toolbar.addWidget(QLabel(label), 0, column)
            toolbar.addWidget(widget, 1, column)
        self.mode_box.setCurrentIndex(1)
        self.edit_profile_btn = QPushButton("Edit profile…")
        self.edit_profile_btn.setObjectName("Secondary")
        self.edit_profile_btn.setAccessibleName("Edit custom voice-leading profile")
        self.edit_profile_btn.clicked.connect(self._edit_profile)

        layout.addLayout(toolbar)
        search_row = QHBoxLayout()
        self.search_seconds = QSpinBox(); self.search_seconds.setRange(1, 600); self.search_seconds.setValue(30)
        self.search_seconds.setAccessibleName("Search time budget in seconds")
        self.search_width = QSpinBox(); self.search_width.setRange(0, 1000); self.search_width.setValue(80)
        self.search_width.setSpecialValueText("Exhaustive")
        self.search_width.setAccessibleName("Search width; zero is exhaustive")
        search_row.addWidget(QLabel("Search seconds")); search_row.addWidget(self.search_seconds)
        search_row.addWidget(QLabel("Search width")); search_row.addWidget(self.search_width)
        paste = QPushButton("Paste assignment…"); paste.clicked.connect(self._paste_assignment)
        paste.setAccessibleName("Paste aligned harmony and voice clues")
        search_row.addWidget(paste)
        search_row.addStretch(1)
        advanced = QWidget(); advanced.setObjectName("PanelBody")
        advanced_layout = QVBoxLayout(advanced)
        options = QGridLayout()
        for col, (label, widget) in enumerate((("Mode", self.mode_box), ("Cadence", self.cadence_box), ("Solutions", self.top_k))):
            options.addWidget(QLabel(label), 0, col); options.addWidget(widget, 1, col)
        options.addWidget(self.edit_profile_btn, 1, 3)
        advanced_layout.addLayout(options)
        advanced_layout.addLayout(search_row)
        help_text = QLabel("Add any number of slots. Enter any mix of S/A/T/B clues; blanks are unknown. "
                           "Chords: G7/B, Dsus4, C9, or notes:C E G Bb. Use Slot constraints for alternatives. "
                           "Four voices reduce extended chords; required tones remain mandatory.")
        help_text.setWordWrap(True); help_text.setObjectName("Subtle"); advanced_layout.addWidget(help_text)

        practice_row = QHBoxLayout()
        practice_row.addWidget(QLabel("Practice type"))
        self.practice_box = QComboBox()
        for practice_type in PracticeType:
            self.practice_box.addItem(
                practice_type.value.replace("-", " ").title(), practice_type.value)
        self.practice_box.setCurrentIndex(self.practice_box.findData(
            PracticeType.PARTIAL_SCORE.value))
        self.practice_box.setAccessibleName("Generated practice type")
        practice_row.addWidget(self.practice_box)
        practice_row.addWidget(QLabel("Difficulty"))
        self.difficulty = QDoubleSpinBox()
        self.difficulty.setRange(0.0, 10.0); self.difficulty.setSingleStep(0.5)
        self.difficulty.setValue(5.0)
        self.difficulty.setAccessibleName("Practice difficulty from zero to ten")
        practice_row.addWidget(self.difficulty)
        self.unique_practice = QCheckBox("Require one solution")
        self.unique_practice.setAccessibleName("Require a uniquely solvable practice")
        practice_row.addWidget(self.unique_practice)
        practice_row.addStretch(1)
        advanced_layout.addLayout(practice_row)

        editor_row = QHBoxLayout()
        actions = []
        for text, name, callback in (
            ("+ Slot", "add_slot_btn", self._add_slot), ("- Slot", "remove_slot_btn", self._remove_slot),
            ("Duplicate", "duplicate_slot_btn", self._duplicate_slot), ("←", "left_btn", self._move_left),
            ("→", "right_btn", self._move_right), ("Lock/Unlock", "lock_btn", self._toggle_lock),
            ("Slot constraints…", "constraints_btn", self._edit_slot_constraints),
            ("Clear unlocked", "clear_btn", self._clear_unlocked),
        ):
            button = QPushButton(text); button.setObjectName("Secondary")
            button.setAccessibleName(text)
            button.clicked.connect(callback)
            setattr(self, name, button); actions.append(button); editor_row.addWidget(button)
        editor_row.addStretch(1)


        self.model = PartWritingTableModel(self.problem, self)
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setAccessibleName("Part-writing constraints table")
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.table.horizontalHeader().setDefaultSectionSize(118)
        self.table.verticalHeader().setDefaultSectionSize(30)
        self.table.setMinimumHeight(285)
        self.table.setAlternatingRowColors(True)

        voice_row = QHBoxLayout()
        voice_row.addWidget(QLabel("Write a voice"))
        self.voice_group = QButtonGroup(self)
        self.voice_buttons = {}
        for voice in VOICE_ORDER:
            button = QPushButton(voice.value.title()); button.setObjectName("Voice")
            button.setCheckable(True); button.setAccessibleName(f"Write {voice.value}")
            button.clicked.connect(lambda checked=False, v=voice: self._choose_voice(v))
            self.voice_group.addButton(button); self.voice_buttons[voice] = button
            voice_row.addWidget(button)
        self.voice_buttons[Voice.SOPRANO].setChecked(True)
        self.accidental_box = QComboBox()
        for label, value in (("In key", None), ("Natural ♮", 0), ("Sharp ♯", 1), ("Flat ♭", -1), ("Double sharp", 2), ("Double flat", -2)):
            self.accidental_box.addItem(label, value)
        self.accidental_box.setAccessibleName("Staff accidental")
        voice_row.addWidget(self.accidental_box)
        layout.addLayout(voice_row)
        self.entry_hint = QLabel("Choose a voice, then click its staff to place a note. Unknown voices stay blank.")
        self.entry_hint.setObjectName("Subtle"); self.entry_hint.setWordWrap(True)
        layout.addWidget(self.entry_hint)
        self.staff = SatbStaffWidget()
        self.staff.noteRequested.connect(self._staff_note)
        self.staff.slotSelected.connect(self._select_slot)
        self.accidental_box.currentIndexChanged.connect(
            lambda: setattr(self.staff, "entry_accidental", self.accidental_box.currentData()))
        self.staff.noteRemoved.connect(self._remove_note)
        score_scroll = QScrollArea(); score_scroll.setWidgetResizable(True)
        score_scroll.setWidget(self.staff); score_scroll.setMinimumHeight(285)
        layout.addWidget(score_scroll)
        self.score_scroll = score_scroll
        self.status = QLabel("Ready · Add notes or solve the I–IV–V–I starting progression.")
        self.status.setObjectName("AccentValue"); self.status.setWordWrap(True)
        self.status.setAccessibleName("Solver status")
        self.piano = PianoWidget(36, 88)
        self.piano.setAccessibleName("Note-entry piano for the selected voice and slot")
        self.piano.notePressed.connect(self._piano_note)
        self.piano.setMinimumHeight(85); self.piano.setMaximumHeight(100)
        self.diagnostics = QTextBrowser()
        self.diagnostics.setAccessibleName("Diagnostics and score explanation")
        self.diagnostics.setMinimumHeight(150)
        self.diagnostics.setPlainText("Start with the score above. Enter the notes you know and leave the rest open.\nSolve harmony finds completions; Check evaluates your writing.")
        commands = QHBoxLayout()
        more_commands = QGridLayout()
        for command_index, (text, name, callback, secondary) in enumerate((
            ("Generate", "generate_btn", self._generate, False),
            ("Solve harmony", "solve_btn", self._start_solve, False),
            ("Stop", "stop_btn", self._stop_solve, True),
            ("Check", "check_btn", self._check, True),
            ("Auto-correct", "auto_correct_btn", self._auto_correct, True),
            ("Explain", "explain_btn", self._explain_selected, True),
            ("Previous", "previous_btn", self._previous_solution, True),
            ("Next", "next_solution_btn", self._next_solution, True),
            ("Reveal", "reveal_btn", self._reveal, True),
            ("Play all", "play_btn", self._play_all, True),
            ("Play voice", "play_voice_btn", self._play_voice, True),
            ("Play chord", "play_chord_btn", self._play_chord, True),
            ("Play transition", "play_transition_btn", self._play_transition, True),
            ("Compare", "compare_btn", self._play_comparison, True),
            ("Save", "save_btn", self._save, True),
            ("Open", "open_btn", self._open, True),
            ("MusicXML", "export_btn", self._export, True),
            ("Reset", "reset_btn", self._reset, True),
        )):
            button = QPushButton(text)
            if secondary:
                button.setObjectName("Secondary")
            button.setAccessibleName(text)
            button.clicked.connect(callback)
            setattr(self, name, button)
            if name in ("solve_btn", "stop_btn", "check_btn", "play_btn"):
                commands.addWidget(button)
            else:
                n = more_commands.count()
                more_commands.addWidget(button, n // 4, n % 4)
        self.stop_btn.setToolTip("Stop playback or cancel the active harmony search")
        self.reveal_btn.setCheckable(True)
        layout.addWidget(self.piano)
        table_panel = QWidget(); table_panel.setObjectName("PanelBody")
        table_layout = QVBoxLayout(table_panel)
        # Two short rows keep every editing command reachable on smaller windows.
        edit_grid = QGridLayout()
        for n, button in enumerate(actions):
            edit_grid.addWidget(button, n // 4, n % 4)
        table_layout.addLayout(edit_grid); table_layout.addWidget(self.table)
        search_row.removeWidget(paste)
        table_layout.insertWidget(0, paste)
        # Put commands with the task they affect, while retaining their names
        # and callbacks for keyboard accessibility and existing integrations.
        while more_commands.count(): more_commands.takeAt(0)
        advanced_layout.addWidget(self.generate_btn)
        table_layout.addWidget(self.auto_correct_btn)
        listen_names = ("previous_btn", "next_solution_btn", "reveal_btn", "explain_btn",
                        "play_voice_btn", "play_chord_btn", "play_transition_btn", "compare_btn",
                        "save_btn", "open_btn", "export_btn", "reset_btn")
        for n, name in enumerate(listen_names):
            more_commands.addWidget(getattr(self, name), n // 4, n % 4)
        action_panel = QWidget(); action_panel.setObjectName("PanelBody"); action_panel.setLayout(more_commands)
        # The score is its own workspace; secondary tasks no longer make the
        # main action disappear below a long accordion of unrelated controls.
        self.editor_tabs = QTabWidget()
        self.editor_tabs.setAccessibleName("Harmony task")
        for page, title in ((host, "Write"), (table_panel, "Assignment"),
                            (advanced, "Practice & rules"), (action_panel, "Listen & files")):
            scroll = QScrollArea(); scroll.setWidgetResizable(True)
            scroll.setWidget(page)
            self.editor_tabs.addTab(scroll, title.replace("&", "&&"))
        shell = QWidget(); outer = QVBoxLayout(shell)
        outer.setContentsMargins(8, 8, 8, 8); outer.setSpacing(10)
        outer.addWidget(self.editor_tabs, 1)
        outer.addWidget(self.status)
        outer.addLayout(commands)
        return shell

    def _disclosure(self, title, content, expanded=False):
        panel = QWidget(); panel.setObjectName("PanelBody")
        box = QVBoxLayout(panel); box.setContentsMargins(0, 0, 0, 0); box.setSpacing(6)
        toggle = QPushButton(("−  " if expanded else "+  ") + title)
        toggle.setObjectName("Disclosure"); toggle.setCheckable(True); toggle.setChecked(expanded)
        toggle.setAccessibleName(title)
        content.setVisible(expanded)
        def change(checked):
            content.setVisible(checked); toggle.setText(("−  " if checked else "+  ") + title)
        toggle.toggled.connect(change)
        box.addWidget(toggle); box.addWidget(content)
        return panel

    def _choose_voice(self, voice):
        self.staff.set_selection(self.staff.selected_slot, voice)
        self._select_slot(self.staff.selected_slot)
        self.entry_hint.setText(f"Writing {voice.value} · click the {'upper' if voice in (Voice.SOPRANO, Voice.ALTO) else 'lower'} staff. Right-click a column or press Delete to remove this voice's note.")

    def _remove_note(self, slot, voice):
        if 0 <= slot < len(self.problem.slots):
            self.problem.slots[slot].voice(voice).pitch = PitchConstraint()
            self.problem.slots[slot].voice(voice).locked = False
            self.model.layoutChanged.emit(); self.model.changed.emit()
            self.status.setText(f"Removed {voice.value} from chord {slot + 1}.")

    def _connect_model(self) -> None:
        self.model.changed.connect(self._problem_changed)
        self.table.selectionModel().currentChanged.connect(self._selection_changed)
        for widget in (self.key_box, self.tonality_box, self.meter_box,
                       self.profile_box, self.cadence_box):
            widget.currentIndexChanged.connect(self._controls_changed)
        self.layout_box.currentIndexChanged.connect(self._layout_changed)

    def _layout_changed(self):
        self.problem.layout = Layout(self.layout_box.currentData())
        self._autosave()
        self._refresh_preview()

    def _restore_problem(self) -> PartWritingProblem:
        raw = self.ctx.db.kv_get("part_writing.autosave", None)
        if isinstance(raw, dict):
            try:
                return problem_from_dict(raw)
            except SerializationError:
                pass
        return _new_problem()

    def _load_controls_from_problem(self) -> None:
        self.key_box.setCurrentText(self.problem.key_tonic)
        self.tonality_box.setCurrentText(self.problem.mode)
        self.meter_box.setCurrentText(f"{self.problem.meter[0]}/{self.problem.meter[1]}")
        index = self.profile_box.findData(self.problem.profile_id)
        self.profile_box.setCurrentIndex(max(0, index))
        index = self.layout_box.findData(self.problem.layout.value)
        self.layout_box.setCurrentIndex(max(0, index))
        cadence = self.problem.cadence.value if self.problem.cadence else ""
        self.cadence_box.setCurrentIndex(max(0, self.cadence_box.findData(cadence)))

    def _sync_controls(self) -> None:
        self.problem.key_tonic = self.key_box.currentText().strip() or "C"
        self.problem.mode = self.tonality_box.currentText()
        num, den = self.meter_box.currentText().split("/")
        self.problem.meter = (int(num), int(den))
        profile_id = self.profile_box.currentData()
        self.problem.profile_id = profile_id
        if profile_id == "custom":
            saved = self.ctx.db.kv_get("part_writing.custom_profile", None)
            if isinstance(saved, dict):
                try:
                    from ...theory.part_writing.serialization import profile_from_dict
                    self.profile = profile_from_dict(saved)
                except SerializationError:
                    self.profile = custom_profile()
            else:
                self.profile = custom_profile()
        else:
            self.profile = profile_for(profile_id)
        self.problem.layout = Layout(self.layout_box.currentData())
        cadence = self.cadence_box.currentData()
        self.problem.cadence = CadenceType(cadence) if cadence else None

    @guard("PartWritingScreen._controls_changed")
    def _controls_changed(self) -> None:
        self._sync_controls()
        self._problem_changed()

    @guard("PartWritingScreen._edit_profile")
    def _edit_profile(self) -> None:
        dialog = RuleProfileDialog(self.profile, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.profile = dialog.profile
            self.ctx.db.kv_set("part_writing.custom_profile", profile_to_dict(self.profile))
            index = self.profile_box.findData("custom")
            self.profile_box.setCurrentIndex(index)
            self.problem.profile_id = "custom"
            self.status.setText("Custom profile saved locally.")
            self._autosave()

    @guard("PartWritingScreen._problem_changed")
    def _problem_changed(self) -> None:
        self._revision = getattr(self, "_revision", 0) + 1
        self.solutions = []
        self.status.setText("Assignment updated · Solve harmony or Check to review these notes.")
        self.diagnostics.setPlainText("The assignment changed. Solve or check again for current feedback.")
        self._autosave()
        self._refresh_preview()

    def _paste_assignment(self) -> None:
        dialog = QDialog(self); dialog.setWindowTitle("Paste an assignment"); dialog.resize(650, 400)
        layout = QVBoxLayout(dialog)
        label = QLabel("Enter aligned rows separated by |. Omit unknown voice rows; use ? for unknown cells. "
                       "Import replaces the table and locks supplied notes. Key/cadence/profile stay selected.")
        label.setWordWrap(True); layout.addWidget(label)
        editor = QPlainTextEdit(); editor.setPlaceholderText(
            "Roman: I | IV | V7 | I\nS: E4 | F4 | ? | E4\nB: C3 | ? | G2 | C3")
        editor.setAccessibleName("Assignment rows"); layout.addWidget(editor)
        error = QLabel(); error.setWordWrap(True); layout.addWidget(error)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        def accept():
            try:
                self._sync_controls()
                problem = parse_assignment(editor.toPlainText(), self.problem)
            except ValueError as exc:
                error.setText(str(exc)); return
            self.problem = problem
            self.model.replace_problem(problem)
            self.practice = None
            self._problem_changed()
            dialog.accept()
        buttons.accepted.connect(accept); buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons); dialog.exec()

    def _autosave(self) -> None:
        self.ctx.db.kv_set("part_writing.autosave", problem_to_dict(self.problem))

    def _current_column(self) -> int:
        index = self.table.currentIndex()
        return index.column() if index.isValid() else max(0, len(self.problem.slots) - 1)

    @guard("PartWritingScreen._selection_changed")
    def _selection_changed(self, current=None, _previous=None) -> None:
        if current is None or not current.isValid():
            return
        voice = _VOICE_ROWS.get(current.row(), self.staff.selected_voice)
        self.staff.set_selection(current.column(), voice)
        self.voice_buttons[voice].setChecked(True)

    @guard("PartWritingScreen._select_slot")
    def _select_slot(self, slot: int) -> None:
        row = next((row for row, voice in _VOICE_ROWS.items()
                    if voice == self.staff.selected_voice), 3)
        self.table.setCurrentIndex(self.model.index(row, slot))

    @guard("PartWritingScreen._add_slot")
    def _add_slot(self) -> None:
        self.model.insert_slot(self._current_column() + 1)

    @guard("PartWritingScreen._remove_slot")
    def _remove_slot(self) -> None:
        self.model.remove_slot(self._current_column())

    @guard("PartWritingScreen._duplicate_slot")
    def _duplicate_slot(self) -> None:
        import copy
        column = self._current_column()
        self.model.insert_slot(column + 1, copy.deepcopy(self.problem.slots[column]))

    def _move(self, delta: int) -> None:
        column = self._current_column(); target = column + delta
        if not 0 <= target < len(self.problem.slots):
            return
        self.model.beginResetModel()
        self.problem.slots[column], self.problem.slots[target] = (
            self.problem.slots[target], self.problem.slots[column])
        self.model.endResetModel()
        self.table.setCurrentIndex(self.model.index(0, target))
        self.model.changed.emit()

    @guard("PartWritingScreen._move_left")
    def _move_left(self) -> None:
        self._move(-1)

    @guard("PartWritingScreen._move_right")
    def _move_right(self) -> None:
        self._move(1)

    @guard("PartWritingScreen._toggle_lock")
    def _toggle_lock(self) -> None:
        indexes = self.table.selectedIndexes() or [self.table.currentIndex()]
        touched = []
        for index in indexes:
            voice = _VOICE_ROWS.get(index.row())
            if voice is None:
                continue
            constraint = self.problem.slots[index.column()].voice(voice)
            constraint.locked = not constraint.locked
            touched.append(index)
        for index in touched:
            self.model.dataChanged.emit(index, index)
        if touched:
            self.model.changed.emit()

    @guard("PartWritingScreen._edit_slot_constraints")
    def _edit_slot_constraints(self) -> None:
        column = self._current_column()
        dialog = SlotConstraintDialog(self.problem.slots[column], column, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if any(self.problem.slots[column].voice(voice).clef is not None
                   for voice in VOICE_ORDER):
                self.problem.layout = Layout.OPEN_SCORE
                self.layout_box.setCurrentIndex(self.layout_box.findData(Layout.OPEN_SCORE.value))
            self.model.changed.emit()

    @guard("PartWritingScreen._clear_unlocked")
    def _clear_unlocked(self) -> None:
        self.model.beginResetModel()
        for slot in self.problem.slots:
            for voice in VOICE_ORDER:
                if not slot.voice(voice).locked:
                    slot.voice(voice).pitch = PitchConstraint()
        self.model.endResetModel(); self.model.changed.emit()

    def _set_exact(self, slot_index: int, voice: Voice, note: Note) -> None:
        if not 0 <= slot_index < len(self.problem.slots):
            return
        self.problem.slots[slot_index].voice(voice).pitch = PitchConstraint(exact=note)
        row = next(row for row, item in _VOICE_ROWS.items() if item == voice)
        index = self.model.index(row, slot_index)
        self.model.dataChanged.emit(index, index); self.model.changed.emit()

    @guard("PartWritingScreen._piano_note")
    def _piano_note(self, midi: int) -> None:
        note = Note.from_midi(int(midi))
        self.ctx.engine.play_note(int(midi), dur=0.45)
        indexes = [index for index in self.table.selectedIndexes()
                   if index.row() in _VOICE_ROWS]
        if indexes:
            for index in indexes:
                self._set_exact(index.column(), _VOICE_ROWS[index.row()], note)
            self.status.setText(f"Added {note.name} to {len(indexes)} selected voice cell(s).")
            return
        index = self.table.currentIndex()
        voice = _VOICE_ROWS.get(index.row(), self.staff.selected_voice)
        self._set_exact(index.column() if index.isValid() else 0, voice, note)
        self.status.setText(f"Added {note.name} · {voice.value.title()}")

    @guard("PartWritingScreen._staff_note")
    def _staff_note(self, slot: int, voice: Voice, note: Note) -> None:
        self._set_exact(slot, voice, note)
        self.ctx.engine.play_note(note.midi, dur=0.45)
        self.status.setText(f"Added {note.name} · {voice.value.title()} · chord {slot + 1}")

    def _entered_voicings(self) -> list[Voicing] | None:
        out = []
        for slot in self.problem.slots:
            notes = [slot.voice(voice).pitch.exact for voice in VOICE_ORDER]
            if any(note is None for note in notes):
                return None
            out.append(Voicing(*notes))
        return out

    def _current_solution(self):
        if not self.solutions:
            return None
        return self.solutions[self.solution_index % len(self.solutions)]

    def _refresh_preview(self, violations=()) -> None:
        solution = self._current_solution()
        voicings = solution.voicings if solution else (self._entered_voicings() or [])
        labels = solution.harmony_labels if solution else [slot.harmony.roman_numeral or slot.harmony.chord_symbol or ""
                                                            for slot in self.problem.slots]
        figures = [slot.harmony.figured_bass or "" for slot in self.problem.slots]
        locked = {(index, voice) for index, slot in enumerate(self.problem.slots)
                  for voice in VOICE_ORDER if slot.voice(voice).locked}
        generated = {(index, voice) for index in range(len(voicings)) for voice in VOICE_ORDER
                     if (index, voice) not in locked and solution is not None}
        marked = {(slot, voice) for violation in violations for slot in violation.slots
                  for voice in violation.voices}
        ghost = self.practice.answer.voicings if self.practice is not None and self.reveal_btn.isChecked() else []
        self.staff.set_layout_mode(self.problem.layout)
        self.staff.set_key(self.problem.key_tonic, self.problem.mode)
        self.staff.set_meter(*self.problem.meter)
        defaults = {Voice.SOPRANO: Clef.TREBLE, Voice.ALTO: Clef.TREBLE,
                    Voice.TENOR: Clef.BASS, Voice.BASS: Clef.BASS}
        clefs = {
            voice: next((slot.voice(voice).clef for slot in self.problem.slots
                         if slot.voice(voice).clef is not None), defaults[voice])
            for voice in VOICE_ORDER
        }
        self.staff.set_clefs(clefs)
        self.staff.set_score(voicings, labels=labels, figures=figures,
                             durations=[slot.duration for slot in self.problem.slots],
                             ghost=ghost, locked=locked, generated=generated, violations=marked,
                             partial=[{voice: slot.voice(voice).pitch.exact for voice in VOICE_ORDER}
                                      for slot in self.problem.slots] if not solution else [])
        self.score_scroll.setMinimumHeight(440 if self.problem.layout == Layout.OPEN_SCORE else 285)
        self.previous_btn.setEnabled(len(self.solutions) > 1)
        self.next_solution_btn.setEnabled(len(self.solutions) > 1)
        self.reveal_btn.setEnabled(self.practice is not None)
        if solution:
            self.status.setText(
                f"Solution {self.solution_index + 1}/{len(self.solutions)} · score {solution.score:.2f}")

    @guard("PartWritingScreen._generate")
    def _generate(self) -> None:
        difficulty = self.difficulty.value()
        practice_type = PracticeType(self.practice_box.currentData())
        self.practice = generate_practice(
            difficulty, random.Random(self.problem.seed or 1), practice_type,
            require_unique=self.unique_practice.isChecked(), profile=self.profile)
        self.problem = self.practice.problem
        self.model.replace_problem(self.problem)
        self._load_controls_from_problem()
        self.solutions = []
        self.reveal_btn.setChecked(False)
        self.status.setText(self.practice.instructions)
        self.diagnostics.setPlainText(
            "Practice generated and independently solved before clues were removed. "
            "Any completion with zero hard violations is accepted.")

    @guard("PartWritingScreen._start_solve")
    def _start_solve(self) -> None:
        if self._thread is not None:
            return
        self._sync_controls(); self._cancel = threading.Event()
        self._solve_revision = getattr(self, "_revision", 0)
        options = SolverOptions(top_k=self.top_k.value(), cancellation=self._cancel,
                                max_nodes=5_000_000, time_limit_seconds=self.search_seconds.value(),
                                beam_width=self.search_width.value())
        import copy
        self._thread = QThread(self)
        self._worker = _SolveWorker(copy.deepcopy(self.problem), self.profile, options)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._solve_progress)
        self._worker.completed.connect(self._solve_finished)
        self._worker.completed.connect(self._thread.quit)
        self._thread.finished.connect(self._thread_finished)
        self.solve_btn.setEnabled(False); self.stop_btn.setEnabled(True)
        self.status.setText("Solving…")
        self._thread.start()

    @guard("PartWritingScreen._solve_progress")
    def _solve_progress(self, completed: int, total: int) -> None:
        self.status.setText(f"Solving slot {completed}/{total}…")

    @guard("PartWritingScreen._solve_finished")
    def _solve_finished(self, payload) -> None:
        if getattr(self, "_solve_revision", 0) != getattr(self, "_revision", 0):
            self.status.setText("Assignment changed during search. Solve again for the current clues.")
            return
        if isinstance(payload, Exception):
            self.status.setText("Solver error")
            self.diagnostics.setPlainText(str(payload)); return
        result: SolveResult = payload
        self.solutions = result.solutions; self.solution_index = 0
        self.status.setText(
            f"{result.message} Visited {result.statistics.nodes_visited:,} nodes in "
            f"{result.statistics.elapsed_seconds:.2f}s.")
        if result.solutions:
            solution = result.solutions[0]
            breakdown = "\n".join(f"• {key}: {value:+.2f}"
                                  for key, value in sorted(solution.score_breakdown.items()))
            self.diagnostics.setPlainText(
                "Valid under the selected profile: zero hard-rule violations.\n\n"
                f"Ranking breakdown (lower is better):\n{breakdown}")
            self._refresh_preview()
        else:
            self.diagnostics.setPlainText(summarize(result.diagnostics))
            self._refresh_preview(result.diagnostics)
            if result.diagnostics:
                issue = result.diagnostics[0]
                self.status.setText(f"{issue.explanation} {issue.correction or ''}")

    @guard("PartWritingScreen._thread_finished")
    def _thread_finished(self) -> None:
        if self._worker is not None:
            self._worker.deleteLater()
        if self._thread is not None:
            self._thread.deleteLater()
        self._worker = None; self._thread = None; self._cancel = None
        self.solve_btn.setEnabled(True)

    @guard("PartWritingScreen._stop_solve")
    def _stop_solve(self) -> None:
        self.ctx.engine.stop()
        if self._cancel is not None:
            self._cancel.set(); self.status.setText("Cancelling…")
        else:
            self.status.setText("Playback stopped.")

    @guard("PartWritingScreen._check")
    def _check(self) -> None:
        entered = self._entered_voicings()
        if entered is None:
            self.status.setText("Checking whether the partial entry can be completed…")
            self._start_solve(); return
        evaluation = check_solution(self.problem, entered, self.profile)
        hard = evaluation.hard_violations
        if hard:
            self.status.setText(f"Invalid: {len(hard)} hard-rule violation{'s' if len(hard) != 1 else ''}")
            self.diagnostics.setPlainText(summarize(evaluation.violations))
        else:
            style = [item for item in evaluation.violations
                     if item.severity != RuleSeverity.HARD_ERROR]
            self.status.setText("Valid under the selected profile")
            self.diagnostics.setPlainText(
                "No hard-rule violations.\n\n" + (summarize(style) if style else
                                                    "No conditional issues were found."))
        self._refresh_preview(evaluation.violations)

    @guard("PartWritingScreen._explain_selected")
    def _explain_selected(self) -> None:
        text = self.diagnostics.toPlainText()
        solution = self._current_solution()
        if solution and solution.evaluation.violations:
            text += "\n\nRule context:\n" + "\n".join(
                f"{item.code.value}: {explain(item.code)}" for item in solution.evaluation.violations)
        else:
            text += ("\n\nHard errors invalidate a solution. Conditional errors depend on profile; "
                     "soft penalties rank valid answers. Parallel fourths are allowed in Common Practice.")
        self.diagnostics.setPlainText(text.strip())

    @guard("PartWritingScreen._auto_correct")
    def _auto_correct(self) -> None:
        entered = self._entered_voicings()
        if entered is None:
            self.status.setText("Auto-correct needs exact pitches in every voice and slot.")
            return
        solution, changes, result = auto_correct(self.problem, entered, self.profile)
        if solution is None:
            self.status.setText(result.message)
            self.diagnostics.setPlainText(summarize(result.diagnostics))
            return
        self.solutions = [solution]; self.solution_index = 0
        self.status.setText(f"Auto-correct changed {len(changes)} note{'s' if len(changes) != 1 else ''}.")
        self.diagnostics.setPlainText(
            "Uninvolved notes remained locked.\n" + ("\n".join(changes) if changes else
                                                       "The entry was already valid."))
        self._refresh_preview()

    @guard("PartWritingScreen._previous_solution")
    def _previous_solution(self) -> None:
        if self.solutions:
            self.solution_index = (self.solution_index - 1) % len(self.solutions); self._refresh_preview()

    @guard("PartWritingScreen._next_solution")
    def _next_solution(self) -> None:
        if self.solutions:
            self.solution_index = (self.solution_index + 1) % len(self.solutions); self._refresh_preview()

    @guard("PartWritingScreen._reveal")
    def _reveal(self) -> None:
        if self.practice is not None:
            self._refresh_preview()

    @guard("PartWritingScreen._play_all")
    def _play_all(self) -> None:
        solution = self._current_solution()
        voicings = solution.voicings if solution else self._entered_voicings()
        if voicings:
            items = [(list(voicing.midi_tuple), slot.duration)
                     for voicing, slot in zip(voicings, self.problem.slots)]
            self.ctx.engine.play_sequence(items, tempo=self.problem.tempo)
        else:
            items = []
            for slot in self.problem.slots:
                notes = [slot.voice(v).pitch.exact for v in VOICE_ORDER]
                midis = [note.midi for note in notes if note is not None]
                items.append((midis or None, slot.duration))
            if any(notes for notes, _ in items):
                self.ctx.engine.play_sequence(items, tempo=self.problem.tempo)
            else:
                self.status.setText("Add a note to the score or solve the harmony before playing.")

    @guard("PartWritingScreen._play_voice")
    def _play_voice(self) -> None:
        solution = self._current_solution(); voicings = solution.voicings if solution else self._entered_voicings()
        if voicings:
            voice = self.staff.selected_voice
            items = [(voicing[voice].midi, slot.duration)
                     for voicing, slot in zip(voicings, self.problem.slots)]
            self.ctx.engine.play_sequence(items, tempo=self.problem.tempo)
        else:
            voice = self.staff.selected_voice
            items = [(slot.voice(voice).pitch.exact.midi if slot.voice(voice).pitch.exact else None,
                      slot.duration) for slot in self.problem.slots]
            if any(note is not None for note, _ in items):
                self.ctx.engine.play_sequence(items, tempo=self.problem.tempo)
            else:
                self.status.setText(f"Add a {voice.value} note before playing this voice.")

    @guard("PartWritingScreen._play_chord")
    def _play_chord(self) -> None:
        solution = self._current_solution(); voicings = solution.voicings if solution else self._entered_voicings()
        if voicings:
            index = min(len(voicings) - 1, self._current_column())
            self.ctx.engine.play_chord(list(voicings[index].midi_tuple))

    @guard("PartWritingScreen._play_transition")
    def _play_transition(self) -> None:
        solution = self._current_solution()
        voicings = solution.voicings if solution else self._entered_voicings()
        if voicings and len(voicings) >= 2:
            end = min(len(voicings) - 1, max(1, self._current_column()))
            items = [(list(voicings[index].midi_tuple), self.problem.slots[index].duration)
                     for index in (end - 1, end)]
            self.ctx.engine.play_sequence(items, tempo=self.problem.tempo)

    @guard("PartWritingScreen._play_comparison")
    def _play_comparison(self) -> None:
        entered = self._entered_voicings()
        solution = self._current_solution()
        if entered and solution:
            items = [(list(voicing.midi_tuple), slot.duration)
                     for voicing, slot in zip(entered, self.problem.slots)]
            items.append((None, 1.0))
            items.extend((list(voicing.midi_tuple), slot.duration)
                         for voicing, slot in zip(solution.voicings, self.problem.slots))
            self.ctx.engine.play_sequence(items, tempo=self.problem.tempo)

    def _save_to_path(self, path: str | Path) -> None:
        self._sync_controls(); save_problem(path, self.problem)
        self.status.setText(f"Saved {Path(path).name}")

    @guard("PartWritingScreen._save")
    def _save(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save part-writing problem", "", "JSON (*.json)")
        if path:
            self._save_to_path(path)

    def _open_from_path(self, path: str | Path) -> None:
        problem = load_problem(path)
        self.problem = problem; self.model.replace_problem(problem)
        self._load_controls_from_problem(); self.solutions = []; self.practice = None
        self.status.setText(f"Opened {Path(path).name}"); self._refresh_preview()

    @guard("PartWritingScreen._open")
    def _open(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open part-writing problem", "", "JSON (*.json)")
        if path:
            self._open_from_path(path)

    def _export_to_path(self, path: str | Path) -> Path:
        solution = self._current_solution()
        if solution is None:
            entered = self._entered_voicings()
            if entered is None:
                raise ValueError("Solve or complete every voice before exporting")
            solution = type("EnteredSolution", (), {
                "voicings": entered,
                "harmony_labels": [slot.harmony.roman_numeral or slot.harmony.chord_symbol or ""
                                   for slot in self.problem.slots],
            })()
        return export_musicxml(path, self.problem, solution)

    @guard("PartWritingScreen._export")
    def _export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export MusicXML", "", "MusicXML (*.musicxml)")
        if path:
            destination = self._export_to_path(path); self.status.setText(f"Exported {destination.name}")

    @guard("PartWritingScreen._reset")
    def _reset(self) -> None:
        self.problem = _new_problem(); self.model.replace_problem(self.problem)
        self.solutions = []; self.practice = None; self._load_controls_from_problem()
        self.status.setText("Reset to a four-chord exercise"); self.diagnostics.clear(); self._refresh_preview()

    def on_show(self) -> None:
        self._refresh_preview()

    def hideEvent(self, event):
        self.ctx.engine.stop()
        super().hideEvent(event)

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._cancel is not None:
            self._cancel.set()
        if self._thread is not None:
            self._thread.quit(); self._thread.wait(1500)
        super().closeEvent(event)
