"""Every generator must produce exercises that grade their own canonical
answer as correct, and multiple-choice answers must appear among the choices."""

from __future__ import annotations

import random

import pytest

from music_theory.exercises.base import InputMode
from music_theory.exercises.registry import all_types, generate, safe_generate


def test_registry_populated():
    types = all_types()
    assert len(types) >= 30
    # the requested first-class features exist
    assert "melodic_dictation" in types
    assert any(t.startswith("pcset_") for t in types)


@pytest.mark.parametrize("etype", all_types())
def test_generator_self_consistent(etype):
    for difficulty in (1.0, 4.0, 7.0):
        for seed in range(6):
            ex = generate(etype, difficulty, random.Random(seed * 13 + int(difficulty)))
            assert ex.grade(ex.answer), f"{etype} failed to self-grade at d={difficulty}"
            if ex.input_mode == InputMode.MULTIPLE_CHOICE:
                assert ex.answer in ex.choices
                assert len(ex.choices) == len(set(ex.choices))


@pytest.mark.parametrize("etype", all_types())
def test_generator_has_required_fields(etype):
    ex = generate(etype, 5.0, random.Random(1))
    assert ex.prompt and ex.skill_id and ex.domain in ("theory", "aural", "piano")
    assert isinstance(ex.input_mode, InputMode)


@pytest.mark.parametrize("etype", all_types())
def test_generator_never_raises_across_full_difficulty_range(etype):
    """Regression guard for the Learn-mode crash: no generator may raise at any
    difficulty (a music21 triple-accidental once aborted the whole app)."""
    rng = random.Random(20240529)
    for i in range(60):
        difficulty = (i % 21) * 0.5  # 0.0 .. 10.0
        ex = generate(etype, difficulty, rng)
        assert ex.grade(ex.answer), f"{etype} self-grade failed at d={difficulty}"


def test_safe_generate_never_raises():
    rng = random.Random(0)
    for etype in all_types():
        for difficulty in (0.0, 5.0, 10.0):
            assert safe_generate(etype, difficulty, rng) is not None
    # even a bogus type yields a usable fallback rather than crashing
    fallback = safe_generate("nonexistent_type", 5.0, rng)
    assert fallback.grade(fallback.answer)
