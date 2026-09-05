"""Offline SATB generator, solver, checker, and teaching engine."""

from .models import (
    CadenceType, ChordFactor, Clef, HarmonyConstraint, HarmonySlot, Layout,
    PartWritingProblem, PartWritingSolution, PitchConstraint, RuleCode,
    RuleEvaluation, RuleSeverity, RuleViolation, SolveResult, SolveStatus,
    SolverOptions, Voice, VoiceConstraint, VoiceRange, Voicing,
)
from .profiles import (
    CLASSROOM_STRICT, COMMON_PRACTICE, PROFILES, SPECIES_COUNTERPOINT,
    RuleProfile, custom_profile, profile_for,
)

__all__ = [
    "CadenceType", "ChordFactor", "Clef", "HarmonyConstraint", "HarmonySlot",
    "Layout", "PartWritingProblem", "PartWritingSolution", "PitchConstraint",
    "RuleCode", "RuleEvaluation", "RuleProfile", "RuleSeverity",
    "RuleViolation", "SolveResult", "SolveStatus", "SolverOptions", "Voice",
    "VoiceConstraint", "VoiceRange", "Voicing", "COMMON_PRACTICE",
    "CLASSROOM_STRICT", "SPECIES_COUNTERPOINT", "PROFILES", "custom_profile",
    "profile_for",
]
