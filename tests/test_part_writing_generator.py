"""Practice generation is reproducible, solvable, and self-grading."""

from __future__ import annotations

import random

import pytest

from music_theory.theory.part_writing.generator import (
    PracticeType, generate_practice, grade_practice,
)
from music_theory.theory.part_writing.models import SolverOptions
from music_theory.theory.part_writing.solver import solve


@pytest.mark.parametrize("difficulty", [0.0, 2.5, 5.0, 7.5, 10.0])
def test_supported_difficulties_always_generate_solvable_self_grading_work(difficulty):
    practice = generate_practice(
        difficulty, random.Random(int(difficulty * 100) + 7),
        PracticeType.PARTIAL_SCORE)
    result = solve(practice.problem, options=SolverOptions(top_k=3))
    assert result.solutions
    assert grade_practice(practice, practice.answer.voicings)
    assert all(grade_practice(practice, answer.voicings)
               for answer in result.solutions)


def test_seeded_generation_is_reproducible():
    first = generate_practice(5.0, random.Random(2026), PracticeType.FILL_BOTH_INNER)
    second = generate_practice(5.0, random.Random(2026), PracticeType.FILL_BOTH_INNER)
    assert first.seed == second.seed
    assert first.instructions == second.instructions
    assert [slot.harmony.roman_numeral for slot in first.problem.slots] == [
        slot.harmony.roman_numeral for slot in second.problem.slots]
    assert [voicing.spelled_tuple for voicing in first.answer.voicings] == [
        voicing.spelled_tuple for voicing in second.answer.voicings]


def test_unique_generation_is_actually_unique():
    practice = generate_practice(
        4.0, random.Random(15), PracticeType.FILL_BOTH_INNER,
        require_unique=True)
    result = solve(practice.problem, options=SolverOptions(top_k=2))
    assert practice.unique and len(result.solutions) == 1


def test_difficulty_changes_material_musical_features():
    easy = generate_practice(1.0, random.Random(9), PracticeType.ROMAN_PROGRESS)
    hard = generate_practice(9.0, random.Random(9), PracticeType.CHROMATIC)
    easy_labels = [slot.harmony.roman_numeral for slot in easy.problem.slots]
    hard_labels = [slot.harmony.roman_numeral for slot in hard.problem.slots]
    assert easy.problem.key_tonic in {"C", "G", "F"}
    assert any("/" in label or label in {"N6", "bVI"} for label in hard_labels)
    assert (easy_labels, easy.problem.mode) != (hard_labels, hard.problem.mode)
