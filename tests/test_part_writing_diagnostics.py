"""Contradictions are isolated before search and explanations stay actionable."""

from __future__ import annotations

from music_theory.theory.part_writing.diagnostics import (
    check_solution, inferred_harmonies, preflight_diagnostics, summarize,
)
from music_theory.theory.part_writing.models import (
    CadenceType, ChordFactor, Clef, HarmonyConstraint, HarmonySlot,
    PartWritingProblem, PitchConstraint, RuleCode, Voice, Voicing,
)
from music_theory.theory.part_writing.profiles import COMMON_PRACTICE
from music_theory.theory.pitch import Note


def V(s, a, t, b):
    return Voicing(*(Note.parse(name) for name in (s, a, t, b)))


def one(label="I"):
    return PartWritingProblem(slots=[HarmonySlot(
        HarmonyConstraint(roman_numeral=label))])


def issue_codes(problem):
    return {item.code for item in preflight_diagnostics(problem, COMMON_PRACTICE)}


def lock(problem, voice, pitch, slot=0, clef=None):
    constraint = problem.slots[slot].voice(voice)
    constraint.pitch = PitchConstraint(exact=Note.parse(pitch))
    constraint.locked = True
    constraint.clef = clef


def test_out_of_range_wrong_chord_and_bad_clef_are_field_specific():
    problem = one("I")
    lock(problem, Voice.SOPRANO, "D6", clef=Clef.BASS)
    issues = preflight_diagnostics(problem, COMMON_PRACTICE)
    assert {RuleCode.RANGE, RuleCode.CHORD_MEMBERSHIP,
            RuleCode.REQUIRED_CONSTRAINT}.issubset({item.code for item in issues})
    assert all(item.field.startswith("slot.0.soprano") for item in issues)


def test_locked_crossing_and_bass_inversion_conflict_are_found_before_search():
    problem = one("I6")
    lock(problem, Voice.SOPRANO, "C4")
    lock(problem, Voice.ALTO, "E4")
    lock(problem, Voice.BASS, "C3")
    issues = preflight_diagnostics(problem, COMMON_PRACTICE)
    assert RuleCode.VOICE_CROSSING in {item.code for item in issues}
    assert any(item.code == RuleCode.INVERSION and item.field == "slot.0.bass"
               for item in issues)


def test_conflicting_labels_doubling_and_forbidden_harmony_are_explained():
    problem = one("V")
    problem.slots[0].harmony.chord_symbol = "F"
    assert RuleCode.HARMONY_LABEL_CONFLICT in issue_codes(problem)

    problem = one("I")
    problem.slots[0].harmony.required_doubling = ChordFactor.ROOT
    for voice, pitch in zip(Voice, ("E5", "G4", "E4", "C3")):
        lock(problem, voice, pitch)
    assert RuleCode.REQUIRED_DOUBLING in issue_codes(problem)

    problem = one("I")
    problem.slots[0].harmony.forbidden_harmonies = ("I",)
    issues = preflight_diagnostics(problem, COMMON_PRACTICE)
    assert any("forbidden" in item.title.lower() for item in issues)


def test_locked_complete_triad_omission_is_named():
    problem = one("I")
    for voice, pitch in zip(Voice, ("G5", "G4", "C4", "C3")):
        lock(problem, voice, pitch)
    assert RuleCode.CHORD_COMPLETENESS in issue_codes(problem)


def test_explicit_harmonies_cannot_contradict_requested_cadence():
    problem = PartWritingProblem(
        slots=[HarmonySlot(HarmonyConstraint(roman_numeral="IV")),
               HarmonySlot(HarmonyConstraint(roman_numeral="I"))],
        cadence=CadenceType.HALF)
    issues = preflight_diagnostics(problem, COMMON_PRACTICE)
    assert any(item.code == RuleCode.CADENCE and item.field == "cadence"
               for item in issues)


def test_unlabelled_tertian_chord_is_inferred_in_root_position_order():
    problem = PartWritingProblem(slots=[HarmonySlot()])
    voicing = V("C5", "G4", "E4", "C3")
    harmonies, issues = inferred_harmonies(problem, [voicing])
    assert not issues
    assert [note.name_no_octave for note in harmonies[0].members] == ["C", "E", "G"]
    assert not check_solution(problem, [voicing]).hard_violations


def test_summary_contains_title_explanation_and_correction():
    problem = one("V")
    lock(problem, Voice.BASS, "B2")
    issues = preflight_diagnostics(problem, COMMON_PRACTICE)
    text = summarize(issues)
    assert "Locked bass contradicts" in text
    assert "Suggested correction" in text
