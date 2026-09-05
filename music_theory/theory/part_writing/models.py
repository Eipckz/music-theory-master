"""Data model for deterministic, profile-driven SATB part writing.

The core package deliberately has no Qt dependency.  Exact :class:`Note`
objects are carried throughout so enharmonic spelling is never discarded.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

from ..pitch import Note


class Voice(str, Enum):
    SOPRANO = "soprano"
    ALTO = "alto"
    TENOR = "tenor"
    BASS = "bass"


VOICE_ORDER = (Voice.SOPRANO, Voice.ALTO, Voice.TENOR, Voice.BASS)


class Clef(str, Enum):
    TREBLE = "treble"
    BASS = "bass"
    ALTO = "alto"
    TENOR = "tenor"


class Layout(str, Enum):
    CHORALE = "chorale"
    PIANO = "piano"
    OPEN_SCORE = "open_score"


class RuleSeverity(str, Enum):
    HARD_ERROR = "hard-error"
    CONDITIONAL_ERROR = "conditional-error"
    SOFT_PENALTY = "soft-penalty"
    PREFERENCE_BONUS = "preference-bonus"
    DISABLED = "disabled"


class RuleCode(str, Enum):
    RANGE = "VL_RANGE"
    VOICE_CROSSING = "VL_VOICE_CROSSING"
    VOICE_OVERLAP = "VL_VOICE_OVERLAP"
    UPPER_SPACING = "VL_UPPER_SPACING"
    FORBIDDEN_UNISON = "VL_FORBIDDEN_UNISON"
    CHORD_MEMBERSHIP = "CHORD_MEMBERSHIP"
    CHORD_COMPLETENESS = "CHORD_COMPLETENESS"
    INVERSION = "CHORD_INVERSION"
    REQUIRED_CONSTRAINT = "CONSTRAINT_REQUIRED"
    REQUIRED_DOUBLING = "CHORD_REQUIRED_DOUBLING"
    DOUBLED_LEADING_TONE = "CHORD_DOUBLED_LEADING_TONE"
    DOUBLED_CHORDAL_SEVENTH = "CHORD_DOUBLED_SEVENTH"
    PARALLEL_UNISON = "VL_PARALLEL_P1"
    PARALLEL_FOURTH = "VL_PARALLEL_P4"
    PARALLEL_FIFTH = "VL_PARALLEL_P5"
    PARALLEL_OCTAVE = "VL_PARALLEL_P8"
    ANTIPARALLEL_PERFECT = "VL_ANTIPARALLEL_PERFECT"
    UNEQUAL_FIFTH = "VL_UNEQUAL_FIFTH"
    HIDDEN_FIFTH = "VL_HIDDEN_P5"
    HIDDEN_OCTAVE = "VL_HIDDEN_P8"
    LEADING_TONE_RESOLUTION = "TENDENCY_LEADING_TONE"
    CHORDAL_SEVENTH_RESOLUTION = "TENDENCY_CHORDAL_SEVENTH"
    AUGMENTED_SIXTH_RESOLUTION = "TENDENCY_AUGMENTED_SIXTH"
    CADENTIAL_SIX_FOUR = "CADENCE_CADENTIAL_64"
    MELODIC_AUGMENTED = "MELODY_AUGMENTED_INTERVAL"
    MELODIC_DIMINISHED = "MELODY_DIMINISHED_INTERVAL"
    MELODIC_SEVENTH = "MELODY_SEVENTH"
    MELODIC_LARGE_LEAP = "MELODY_LARGE_LEAP"
    MELODIC_LEAP_RECOVERY = "MELODY_LEAP_RECOVERY"
    CONSECUTIVE_LEAPS = "MELODY_CONSECUTIVE_LEAPS"
    CADENCE = "CADENCE_REQUIREMENT"
    HARMONY_LABEL_CONFLICT = "HARMONY_LABEL_CONFLICT"
    UNSUPPORTED_HARMONY = "HARMONY_UNSUPPORTED"
    SOFT_TOTAL_MOTION = "STYLE_TOTAL_MOTION"
    SOFT_COMMON_TONE = "STYLE_COMMON_TONE"
    SOFT_STEPWISE = "STYLE_STEPWISE"
    SOFT_CONTRARY_BASS = "STYLE_CONTRARY_BASS"
    SOFT_RANGE_EXTREME = "STYLE_RANGE_EXTREME"
    SOFT_ALL_SIMILAR = "STYLE_ALL_SIMILAR"
    SOFT_REPEATED_SOPRANO = "STYLE_REPEATED_SOPRANO"
    SOFT_INCOMPLETE_CHORD = "STYLE_INCOMPLETE_CHORD"


class SolveStatus(str, Enum):
    SOLVED = "solved"
    NO_SOLUTION = "no-solution"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    INVALID_INPUT = "invalid-input"


class CadenceType(str, Enum):
    PERFECT_AUTHENTIC = "perfect-authentic"
    IMPERFECT_AUTHENTIC = "imperfect-authentic"
    HALF = "half"
    DECEPTIVE = "deceptive"
    PLAGAL = "plagal"


class ChordFactor(str, Enum):
    ROOT = "root"
    SECOND = "second"
    THIRD = "third"
    FOURTH = "fourth"
    FIFTH = "fifth"
    SIXTH = "sixth"
    SEVENTH = "seventh"


@dataclass(frozen=True)
class VoiceRange:
    minimum: Note
    maximum: Note

    def contains(self, note: Note) -> bool:
        return self.minimum.midi <= note.midi <= self.maximum.midi


@dataclass
class PitchConstraint:
    """One or more compatible requirements for a single sounding pitch."""

    exact: Optional[Note] = None
    pitch_class: Optional[Note] = None
    scale_degree: Optional[int] = None
    chord_factor: Optional[ChordFactor] = None
    allowed_pitches: tuple[Note, ...] = ()
    minimum: Optional[Note] = None
    maximum: Optional[Note] = None

    @property
    def unrestricted(self) -> bool:
        return not any((self.exact, self.pitch_class, self.scale_degree,
                        self.chord_factor, self.allowed_pitches,
                        self.minimum, self.maximum))


@dataclass
class VoiceConstraint:
    pitch: PitchConstraint = field(default_factory=PitchConstraint)
    locked: bool = False
    clef: Optional[Clef] = None
    note: str = ""
    source_label: str = ""


@dataclass(frozen=True)
class RequiredOccurrence:
    factor: ChordFactor
    count: int = 1


@dataclass
class HarmonyConstraint:
    roman_numeral: Optional[str] = None
    chord_symbol: Optional[str] = None
    figured_bass: Optional[str] = None
    inversion: Optional[int] = None
    exact_bass_pitch: Optional[Note] = None
    required_chord_tones: tuple[str, ...] = ()
    forbidden_chord_tones: tuple[str, ...] = ()
    required_doubling: Optional[ChordFactor] = None
    allowed_harmonies: tuple[str, ...] = ()
    forbidden_harmonies: tuple[str, ...] = ()


def _default_voice_constraints() -> dict[Voice, VoiceConstraint]:
    return {voice: VoiceConstraint() for voice in VOICE_ORDER}


@dataclass
class HarmonySlot:
    harmony: HarmonyConstraint = field(default_factory=HarmonyConstraint)
    voices: dict[Voice, VoiceConstraint] = field(default_factory=_default_voice_constraints)
    duration: float = 1.0
    cadence_role: str = ""
    label: str = ""

    def voice(self, voice: Voice) -> VoiceConstraint:
        return self.voices.setdefault(voice, VoiceConstraint())


@dataclass
class PartWritingProblem:
    key_tonic: str = "C"
    mode: str = "major"
    meter: tuple[int, int] = (4, 4)
    slots: list[HarmonySlot] = field(default_factory=list)
    cadence: Optional[CadenceType] = None
    profile_id: str = "common-practice"
    layout: Layout = Layout.CHORALE
    tempo: int = 84
    title: str = "Part-writing exercise"
    seed: int = 0


@dataclass(frozen=True)
class Voicing:
    soprano: Note
    alto: Note
    tenor: Note
    bass: Note

    def __getitem__(self, voice: Voice) -> Note:
        return {
            Voice.SOPRANO: self.soprano,
            Voice.ALTO: self.alto,
            Voice.TENOR: self.tenor,
            Voice.BASS: self.bass,
        }[voice]

    @property
    def notes(self) -> tuple[Note, Note, Note, Note]:
        return self.soprano, self.alto, self.tenor, self.bass

    @property
    def midi_tuple(self) -> tuple[int, int, int, int]:
        return tuple(note.midi for note in self.notes)

    @property
    def spelled_tuple(self) -> tuple[str, str, str, str]:
        return tuple(note.name for note in self.notes)

    def as_dict(self) -> dict[Voice, Note]:
        return {voice: self[voice] for voice in VOICE_ORDER}


@dataclass(frozen=True)
class RuleViolation:
    code: RuleCode
    severity: RuleSeverity
    title: str
    explanation: str
    slots: tuple[int, ...] = ()
    voices: tuple[Voice, ...] = ()
    notes: tuple[str, ...] = ()
    correction: str = ""
    field: str = ""


@dataclass
class RuleEvaluation:
    violations: list[RuleViolation] = field(default_factory=list)
    soft_score: float = 0.0
    score_breakdown: dict[str, float] = field(default_factory=dict)

    @property
    def hard_violations(self) -> list[RuleViolation]:
        return [v for v in self.violations if v.severity == RuleSeverity.HARD_ERROR]

    @property
    def valid(self) -> bool:
        return not self.hard_violations

    def extend(self, other: "RuleEvaluation") -> None:
        self.violations.extend(other.violations)
        self.soft_score += other.soft_score
        for key, value in other.score_breakdown.items():
            self.score_breakdown[key] = self.score_breakdown.get(key, 0.0) + value


@dataclass
class PartWritingSolution:
    voicings: list[Voicing]
    score: float
    score_breakdown: dict[str, float] = field(default_factory=dict)
    evaluation: RuleEvaluation = field(default_factory=RuleEvaluation)
    harmony_labels: list[str] = field(default_factory=list)


@dataclass
class SolveStatistics:
    nodes_visited: int = 0
    local_candidates: int = 0
    transitions_checked: int = 0
    rejected_local: int = 0
    rejected_transitions: int = 0
    elapsed_seconds: float = 0.0


@dataclass
class SolveResult:
    status: SolveStatus
    solutions: list[PartWritingSolution] = field(default_factory=list)
    diagnostics: list[RuleViolation] = field(default_factory=list)
    statistics: SolveStatistics = field(default_factory=SolveStatistics)
    message: str = ""


@dataclass
class SolverOptions:
    top_k: int = 5
    max_nodes: int = 250_000
    time_limit_seconds: float = 12.0
    cancellation: Optional[threading.Event] = None
    progress_callback: Optional[Callable[[int, int], None]] = None
    validate_harmonic_grammar: bool = False
    beam_width: int = 0  # zero retains exhaustive ranking; positive bounds live paths

    def normalized(self) -> "SolverOptions":
        return SolverOptions(
            top_k=max(1, min(20, int(self.top_k))),
            max_nodes=max(1, int(self.max_nodes)),
            time_limit_seconds=max(0.01, float(self.time_limit_seconds)),
            cancellation=self.cancellation,
            progress_callback=self.progress_callback,
            validate_harmonic_grammar=bool(self.validate_harmonic_grammar),
            beam_width=max(0, int(self.beam_width)),
        )
