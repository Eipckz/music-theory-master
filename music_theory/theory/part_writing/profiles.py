"""Selectable rule profiles and locally serializable custom settings."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from ..pitch import Note
from .models import RuleCode, RuleSeverity, Voice, VoiceRange


DEFAULT_RANGES = {
    Voice.SOPRANO: VoiceRange(Note.parse("C4"), Note.parse("G5")),
    Voice.ALTO: VoiceRange(Note.parse("G3"), Note.parse("D5")),
    Voice.TENOR: VoiceRange(Note.parse("C3"), Note.parse("G4")),
    Voice.BASS: VoiceRange(Note.parse("E2"), Note.parse("C4")),
}


def _common_rules() -> dict[RuleCode, RuleSeverity]:
    hard = {
        RuleCode.RANGE, RuleCode.VOICE_CROSSING, RuleCode.VOICE_OVERLAP,
        RuleCode.UPPER_SPACING, RuleCode.CHORD_MEMBERSHIP,
        RuleCode.CHORD_COMPLETENESS, RuleCode.INVERSION,
        RuleCode.REQUIRED_CONSTRAINT, RuleCode.REQUIRED_DOUBLING,
        RuleCode.DOUBLED_LEADING_TONE, RuleCode.DOUBLED_CHORDAL_SEVENTH,
        RuleCode.PARALLEL_UNISON, RuleCode.PARALLEL_FIFTH,
        RuleCode.PARALLEL_OCTAVE, RuleCode.LEADING_TONE_RESOLUTION,
        RuleCode.CHORDAL_SEVENTH_RESOLUTION,
        RuleCode.AUGMENTED_SIXTH_RESOLUTION, RuleCode.CADENTIAL_SIX_FOUR,
        RuleCode.MELODIC_AUGMENTED, RuleCode.MELODIC_SEVENTH,
        RuleCode.CADENCE, RuleCode.HARMONY_LABEL_CONFLICT,
        RuleCode.UNSUPPORTED_HARMONY,
    }
    conditional = {
        RuleCode.HIDDEN_FIFTH, RuleCode.HIDDEN_OCTAVE,
        RuleCode.UNEQUAL_FIFTH, RuleCode.MELODIC_DIMINISHED,
        RuleCode.MELODIC_LARGE_LEAP, RuleCode.MELODIC_LEAP_RECOVERY,
        RuleCode.CONSECUTIVE_LEAPS,
    }
    rules = {code: RuleSeverity.DISABLED for code in RuleCode}
    rules.update({code: RuleSeverity.HARD_ERROR for code in hard})
    rules.update({code: RuleSeverity.CONDITIONAL_ERROR for code in conditional})
    rules[RuleCode.PARALLEL_FOURTH] = RuleSeverity.DISABLED
    rules[RuleCode.ANTIPARALLEL_PERFECT] = RuleSeverity.DISABLED
    rules[RuleCode.FORBIDDEN_UNISON] = RuleSeverity.DISABLED
    return rules


DEFAULT_WEIGHTS = {
    "total_motion": 1.0,
    "common_tone": -2.5,
    "stepwise_upper": -1.5,
    "contrary_bass": -1.0,
    "range_extreme": 2.0,
    "large_soprano_leap": 3.0,
    "all_similar": 4.0,
    "repeated_soprano": 0.75,
    "incomplete_chord": 2.0,
    "root_doubling": -1.0,
    "balanced_spacing": 0.25,
}


@dataclass
class RuleProfile:
    id: str
    name: str
    description: str
    severities: dict[RuleCode, RuleSeverity] = field(default_factory=_common_rules)
    weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))
    voice_ranges: dict[Voice, VoiceRange] = field(
        default_factory=lambda: dict(DEFAULT_RANGES))
    max_melodic_leap: int = 9
    large_leap_threshold: int = 5
    max_tenor_bass_spacing: int = 19
    require_complete_triads: bool = True
    allow_incomplete_dominant_seventh: bool = True
    permit_voice_unisons: bool = True
    treat_compound_perfects: bool = True
    permit_unequal_fifths: bool = True
    inner_leading_tone_exception: bool = False
    strict_hidden_perfects: bool = False
    strict_cadential_soprano: bool = True

    def severity(self, code: RuleCode) -> RuleSeverity:
        return self.severities.get(code, RuleSeverity.DISABLED)

    def with_rule(self, code: RuleCode, severity: RuleSeverity) -> "RuleProfile":
        rules = dict(self.severities)
        rules[code] = severity
        return replace(self, severities=rules)


COMMON_PRACTICE = RuleProfile(
    id="common-practice",
    name="Common Practice",
    description="Standard chorale-style undergraduate tonal-harmony rules.",
)


def _strict_profile() -> RuleProfile:
    severities = dict(_common_rules())
    for code in (
        RuleCode.PARALLEL_FOURTH, RuleCode.ANTIPARALLEL_PERFECT,
        RuleCode.HIDDEN_FIFTH, RuleCode.HIDDEN_OCTAVE,
        RuleCode.UNEQUAL_FIFTH, RuleCode.MELODIC_DIMINISHED,
        RuleCode.MELODIC_LARGE_LEAP, RuleCode.MELODIC_LEAP_RECOVERY,
        RuleCode.CONSECUTIVE_LEAPS,
    ):
        severities[code] = RuleSeverity.HARD_ERROR
    return RuleProfile(
        id="classroom-strict",
        name="Classroom Strict",
        description="Conservative assignment grading with stricter perfect-interval and melodic rules.",
        severities=severities,
        max_melodic_leap=8,
        permit_unequal_fifths=False,
        strict_hidden_perfects=True,
    )


CLASSROOM_STRICT = _strict_profile()


def _species_profile() -> RuleProfile:
    profile = _strict_profile()
    profile.id = "species-counterpoint"
    profile.name = "Species Counterpoint"
    profile.description = "A stricter melodic and direct-interval profile for species work."
    profile.max_melodic_leap = 7
    profile.permit_voice_unisons = False
    profile.severities[RuleCode.FORBIDDEN_UNISON] = RuleSeverity.HARD_ERROR
    return profile


SPECIES_COUNTERPOINT = _species_profile()

PROFILES = {
    COMMON_PRACTICE.id: COMMON_PRACTICE,
    CLASSROOM_STRICT.id: CLASSROOM_STRICT,
    SPECIES_COUNTERPOINT.id: SPECIES_COUNTERPOINT,
}


def custom_profile(base: RuleProfile = COMMON_PRACTICE, *, name: str = "Custom") -> RuleProfile:
    return RuleProfile(
        id="custom",
        name=name,
        description="Instructor-configurable local rule profile.",
        severities=dict(base.severities),
        weights=dict(base.weights),
        voice_ranges=dict(base.voice_ranges),
        max_melodic_leap=base.max_melodic_leap,
        large_leap_threshold=base.large_leap_threshold,
        max_tenor_bass_spacing=base.max_tenor_bass_spacing,
        require_complete_triads=base.require_complete_triads,
        allow_incomplete_dominant_seventh=base.allow_incomplete_dominant_seventh,
        permit_voice_unisons=base.permit_voice_unisons,
        treat_compound_perfects=base.treat_compound_perfects,
        permit_unequal_fifths=base.permit_unequal_fifths,
        inner_leading_tone_exception=base.inner_leading_tone_exception,
        strict_hidden_perfects=base.strict_hidden_perfects,
        strict_cadential_soprano=base.strict_cadential_soprano,
    )


def profile_for(profile_id: str) -> RuleProfile:
    return PROFILES.get(profile_id, COMMON_PRACTICE)
