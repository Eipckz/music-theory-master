"""End-to-end contracts for the deterministic layered SATB solver."""

from __future__ import annotations

import threading

from music_theory.theory.part_writing.models import (
    CadenceType, Clef, HarmonyConstraint, HarmonySlot, PartWritingProblem,
    PitchConstraint, SolveStatus, SolverOptions, Voice, Voicing,
)
from music_theory.theory.part_writing.solver import (
    auto_correct, solve, validate_returned_solution,
)
from music_theory.theory.pitch import Note


def progression(labels, *, cadence=None, key="C", mode="major"):
    return PartWritingProblem(
        key_tonic=key, mode=mode,
        slots=[HarmonySlot(HarmonyConstraint(roman_numeral=label)) for label in labels],
        cadence=cadence,
    )


def assert_every_solution_valid(problem, result):
    assert result.status == SolveStatus.SOLVED, result.message
    assert result.solutions
    for solution in result.solutions:
        assert not validate_returned_solution(problem, solution).hard_violations


def test_solves_textbook_progression_and_returns_distinct_ranked_answers():
    problem = progression(("I", "ii6", "V7", "I"),
                          cadence=CadenceType.PERFECT_AUTHENTIC)
    result = solve(problem, options=SolverOptions(top_k=4))
    assert_every_solution_valid(problem, result)
    identities = {tuple(voicing.spelled_tuple for voicing in solution.voicings)
                  for solution in result.solutions}
    assert len(identities) == len(result.solutions) >= 2
    assert [solution.score for solution in result.solutions] == sorted(
        solution.score for solution in result.solutions)


def test_figured_bass_inversion_fixed_outer_and_inner_voices_are_exact():
    problem = progression(("I", "IV", "V", "I"))
    problem.slots[0].harmony.figured_bass = "6"
    problem.slots[0].harmony.inversion = 1
    locks = {
        (0, Voice.BASS): "E3",
        (1, Voice.SOPRANO): "C5",
        (2, Voice.ALTO): "D4",
        (2, Voice.TENOR): "B3",
        (3, Voice.BASS): "C3",
    }
    for (slot, voice), pitch in locks.items():
        constraint = problem.slots[slot].voice(voice)
        constraint.pitch = PitchConstraint(exact=Note.parse(pitch))
        constraint.locked = True
    result = solve(problem, options=SolverOptions(top_k=3))
    assert_every_solution_valid(problem, result)
    for solution in result.solutions:
        for (slot, voice), pitch in locks.items():
            assert solution.voicings[slot][voice].name == pitch


def test_pitch_class_enharmonic_spelling_and_clef_metadata_are_honored():
    problem = progression(("I", "IV", "V", "I"), key="Bb")
    problem.slots[0].voice(Voice.SOPRANO).pitch = PitchConstraint(
        pitch_class=Note.parse("Bb"))
    problem.slots[0].voice(Voice.SOPRANO).clef = Clef.TREBLE
    problem.slots[0].voice(Voice.ALTO).clef = Clef.ALTO
    problem.slots[0].voice(Voice.TENOR).clef = Clef.TENOR
    problem.slots[0].voice(Voice.BASS).clef = Clef.BASS
    result = solve(problem, options=SolverOptions(top_k=2))
    assert_every_solution_valid(problem, result)
    assert all(solution.voicings[0].soprano.name_no_octave == "Bb"
               for solution in result.solutions)
    assert problem.slots[0].voice(Voice.ALTO).clef == Clef.ALTO


def test_solver_is_deterministic_for_identical_input_and_options():
    problem = progression(("I", "IV", "V", "I"))
    options = SolverOptions(top_k=3)
    first = solve(problem, options=options)
    second = solve(problem, options=options)
    assert_every_solution_valid(problem, first)
    assert [tuple(v.spelled_tuple for v in s.voicings) for s in first.solutions] == [
        tuple(v.spelled_tuple for v in s.voicings) for s in second.solutions]
    assert [s.score for s in first.solutions] == [s.score for s in second.solutions]


def test_contradictory_locked_bass_is_rejected_with_field_diagnostic():
    problem = progression(("V", "I"))
    bass = problem.slots[0].voice(Voice.BASS)
    bass.pitch = PitchConstraint(exact=Note.parse("B2"))
    bass.locked = True
    result = solve(problem)
    assert result.status == SolveStatus.INVALID_INPUT
    assert any(item.field == "slot.0.bass" for item in result.diagnostics)
    assert "conflict" in result.message.lower()


def test_eight_and_sixteen_slot_progressions_finish_within_documented_bound():
    for count, seconds in ((8, 8.0), (16, 12.0)):
        labels = (("I", "IV", "V", "I") * 4)[:count]
        problem = progression(labels)
        result = solve(problem, options=SolverOptions(
            top_k=1, max_nodes=750_000, time_limit_seconds=seconds))
        assert_every_solution_valid(problem, result)
        assert result.statistics.elapsed_seconds < seconds


def test_cancellation_and_timeout_are_honest_terminal_states():
    problem = progression(("I", "IV", "V", "I"))
    cancellation = threading.Event(); cancellation.set()
    cancelled = solve(problem, options=SolverOptions(cancellation=cancellation))
    assert cancelled.status == SolveStatus.CANCELLED and not cancelled.solutions
    timed = solve(problem, options=SolverOptions(top_k=1, max_nodes=1,
                                                  time_limit_seconds=10))
    assert timed.status == SolveStatus.TIMEOUT and not timed.solutions


def test_auto_correct_changes_only_involved_cells_and_revalidates():
    problem = progression(("I", "IV", "V", "I"))
    original = solve(problem, options=SolverOptions(top_k=1)).solutions[0]
    entered = list(original.voicings)
    source = entered[1]
    entered[1] = Voicing(source.soprano, Note.parse("F#4"),
                         source.tenor, source.bass)
    corrected, changes, result = auto_correct(problem, entered)
    assert corrected is not None and result.solutions
    assert changes and all("Slot 2 alto" in change for change in changes)
    assert not validate_returned_solution(problem, corrected).hard_violations
    for index, (before, after) in enumerate(zip(entered, corrected.voicings)):
        for voice in Voice:
            if (index, voice) != (1, Voice.ALTO):
                assert before[voice] == after[voice]
