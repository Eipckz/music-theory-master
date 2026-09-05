"""Regression scenarios from partial college assignments, not just parser round trips."""
import copy
import random
import threading

import pytest

from music_theory.curriculum import CURRICULUM
from music_theory.curriculum.lessons import lesson_for
from music_theory.exercises.registry import generate
from music_theory.theory.part_writing.harmony import harmonies_for_slot, normalize_constraint
from music_theory.theory.part_writing.models import (
    HarmonyConstraint, HarmonySlot, PartWritingProblem, PitchConstraint,
    RuleCode, RuleSeverity, SolverOptions, SolveStatus, VOICE_ORDER,
)
from music_theory.theory.part_writing.profiles import custom_profile
from music_theory.theory.part_writing.solver import solve, validate_returned_solution
from music_theory.theory.part_writing.voicings import enumerate_voicings, clear_voicing_cache
from music_theory.theory.pitch import Note


def given(slot, names):
    for voice, name in zip(VOICE_ORDER, names.split()):
        slot.voice(voice).pitch = PitchConstraint(exact=Note.parse(name))
        slot.voice(voice).locked = True


def test_unknown_first_chord_can_be_inverted_subdominant():
    problem = PartWritingProblem(slots=[HarmonySlot()])
    given(problem.slots[0], "F4 C4 A3 A2")
    result = solve(problem, options=SolverOptions(top_k=3))
    assert result.status == SolveStatus.SOLVED, result.message
    assert "IV6" in [s.harmony_labels[0] for s in result.solutions]
    assert all(not validate_returned_solution(problem, s).hard_violations for s in result.solutions)


def test_forty_event_assignment_preserves_every_given_and_roundtrips():
    from music_theory.theory.part_writing.serialization import problem_to_dict, problem_from_dict
    slot = HarmonySlot(HarmonyConstraint(roman_numeral="I"))
    given(slot, "E4 C4 G3 C3")
    problem = PartWritingProblem(slots=[copy.deepcopy(slot) for _ in range(40)])
    loaded = problem_from_dict(problem_to_dict(problem))
    result = solve(loaded, options=SolverOptions(top_k=1, beam_width=20))
    assert result.status == SolveStatus.SOLVED, result.message
    assert len(result.solutions[0].voicings) == 40
    assert all(v.spelled_tuple == ("E4", "C4", "G3", "C3") for v in result.solutions[0].voicings)


@pytest.mark.parametrize("symbol,expected", [
    ("Dsus4", {"D", "G", "A"}), ("C9", {"C", "E", "G", "Bb", "D"}),
    ("Bbmaj7", {"Bb", "D", "F", "A"}), ("notes:C E G Bb", {"C", "E", "G", "Bb"}),
    ("F#m7/C#", {"F#", "A", "C#", "E"}),
])
def test_extended_and_custom_chords_keep_spelling(symbol, expected):
    harmony = normalize_constraint(HarmonyConstraint(chord_symbol=symbol), "C", "major")
    assert {n.name_no_octave for n in harmony.members} == expected
    assert len(harmony.factors) == len(harmony.members)


def test_ninth_reduction_keeps_third_seventh_ninth_and_required_bass():
    problem = PartWritingProblem(slots=[HarmonySlot(HarmonyConstraint(chord_symbol="C9"))])
    result = solve(problem)
    assert result.status == SolveStatus.SOLVED, result.message
    assert all({n.name_no_octave for n in s.voicings[0].notes} == {"C", "E", "Bb", "D"}
               for s in result.solutions)
    problem.slots[0].harmony.required_chord_tones = ("G",)
    assert solve(problem).status == SolveStatus.NO_SOLUTION  # cannot fit five mandatory tones in SATB


def test_symbol_alternatives_are_not_silently_discarded():
    p = PartWritingProblem(slots=[HarmonySlot(HarmonyConstraint(allowed_harmonies=("Dm7", "V7/V", "Dsus4")))])
    assert {h.label for h in harmonies_for_slot(p, 0)} == {"Dm7", "V7/V", "Dsus4"}


def test_profile_cache_does_not_reuse_a_previous_severity():
    clear_voicing_cache()
    p = PartWritingProblem(slots=[HarmonySlot(HarmonyConstraint(roman_numeral="I"))])
    h = harmonies_for_slot(p, 0)[0]
    strict = custom_profile()
    relaxed = custom_profile()
    relaxed.severities[RuleCode.CHORD_COMPLETENESS] = RuleSeverity.DISABLED
    first = enumerate_voicings(p, 0, h, strict, maximum=None)
    second = enumerate_voicings(p, 0, h, relaxed, maximum=None)
    assert len(second) > len(first)


def test_candidate_enumeration_can_be_interrupted():
    clear_voicing_cache()
    p = PartWritingProblem(slots=[HarmonySlot(HarmonyConstraint(roman_numeral="I"))])
    h = harmonies_for_slot(p, 0)[0]
    def stop():
        raise InterruptedError("stop")
    with pytest.raises(InterruptedError):
        enumerate_voicings(p, 0, h, custom_profile(), check_limits=stop)
    cancelled = threading.Event(); cancelled.set()
    assert solve(p, options=SolverOptions(cancellation=cancelled)).status == SolveStatus.CANCELLED


def test_paste_mixed_clues_and_reject_misalignment_atomically():
    from music_theory.ui.screens.part_writing import parse_assignment
    template = PartWritingProblem(key_tonic="Bb", slots=[HarmonySlot()])
    p = parse_assignment("Roman: I | ? | V7\nS: D5 | ? | A4\nB: ? | Eb3 | F3", template)
    assert len(p.slots) == 3 and p.key_tonic == "Bb"
    assert p.slots[0].voice(VOICE_ORDER[0]).locked
    assert p.slots[1].voice(VOICE_ORDER[-1]).pitch.exact.name == "Eb3"
    assert len(template.slots) == 1
    with pytest.raises(ValueError, match="same number"):
        parse_assignment("S: D5 | C5\nB: Bb2", template)
    with pytest.raises(ValueError):
        parse_assignment("", template)


def test_tonal_path_has_lessons_drills_and_connects_to_posttonal():
    skills = [s for s in CURRICULUM if s.id.startswith("tonal.")]
    assert len(skills) == 7
    for skill in skills:
        assert len(lesson_for(skill.id)) >= 3
        for etype in skill.etypes:
            for difficulty in (0, 4, 7, 10):
                for seed in range(8):
                    ex = generate(etype, difficulty, random.Random(seed))
                    assert ex.skill_id == skill.id and ex.grade(ex.answer)
                    assert ex.answer in ex.choices and len(set(ex.choices)) == len(ex.choices)
                    assert not ex.grade("not a musical answer")
    assert "tonal.modulation" in CURRICULUM.get("harmony.chromatic").prereqs
    assert "harmony.chromatic" in CURRICULUM.get("posttonal.pitch_classes").prereqs


def test_third_rises_seventh_falls_in_many_keys():
    from music_theory.theory.chords import roman_to_chord
    for seed in range(40):
        ex = generate("dominant_tendency", 7, random.Random(seed))
        key, mode = ex.prompt.split()[1:3]
        mode = mode.rstrip(",")
        tonic = roman_to_chord("I" if mode == "major" else "i", key, mode)
        expected = tonic.members[0 if "third (leading tone)" in ex.prompt else 1].name_no_octave
        assert ex.answer == expected


def test_musical_case_is_not_discarded_when_grading():
    from music_theory.exercises.base import Exercise, InputMode
    for correct, wrong in (("M3", "m3"), ("IV", "iv"), ("V/ii", "V/II")):
        ex = Exercise("test", "theory", "test", "test", InputMode.MULTIPLE_CHOICE, correct)
        assert ex.grade(correct)
        assert not ex.grade(wrong)


@pytest.mark.parametrize("labels,notes", [
    (("V7", "V7"), ("F4 D4 B3 G2", "F4 D4 B3 G2")),
    (("Fr+6", "V"), ("F#4 D4 C4 Ab2", "G4 D4 B3 G2")),
])
def test_prolonged_dominant_and_french_sixth_do_not_get_false_seventh_errors(labels, notes):
    p = PartWritingProblem(slots=[HarmonySlot(HarmonyConstraint(roman_numeral=x)) for x in labels])
    for slot, pitches in zip(p.slots, notes):
        given(slot, pitches)
    result = solve(p)
    assert result.status == SolveStatus.SOLVED, result.message
    assert not validate_returned_solution(p, result.solutions[0]).hard_violations
