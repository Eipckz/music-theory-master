"""Shared helpers for exercise generators."""

from __future__ import annotations

import random
from typing import Sequence

from ..theory.pitch import Note

# Keys grouped by difficulty (number of accidentals).
EASY_KEYS = ["C", "G", "F", "D", "Bb"]
MED_KEYS = EASY_KEYS + ["A", "Eb", "E", "Ab"]
HARD_KEYS = MED_KEYS + ["B", "Db", "F#", "Gb", "C#", "Cb"]


def band(difficulty: float) -> int:
    """Map a continuous difficulty to a 0..4 band."""
    return max(0, min(4, int(difficulty // 2)))


def pick_key_name(rng: random.Random, difficulty: float) -> str:
    pool = EASY_KEYS if difficulty < 3 else MED_KEYS if difficulty < 6 else HARD_KEYS
    return rng.choice(pool)


def pick_mode(rng: random.Random, difficulty: float) -> str:
    if difficulty < 2:
        return "major"
    return rng.choice(["major", "minor"])


def choices_from(correct: str, distractors: Sequence[str], rng: random.Random, k: int = 4) -> list[str]:
    pool = [d for d in dict.fromkeys(distractors) if d != correct]
    rng.shuffle(pool)
    opts = [correct] + pool[: max(1, k - 1)]
    opts = list(dict.fromkeys(opts))
    rng.shuffle(opts)
    return opts


def random_midi(rng: random.Random, low: int, high: int, white_only: bool = False) -> int:
    while True:
        m = rng.randint(low, high)
        if not white_only or (m % 12) in (0, 2, 4, 5, 7, 9, 11):
            return m


def note_in_clef_range(rng: random.Random, clef: str, easy: bool = True) -> Note:
    if clef == "bass":
        low, high = (40, 60) if easy else (36, 64)
    else:
        low, high = (60, 79) if easy else (55, 84)
    return Note.from_midi(random_midi(rng, low, high, white_only=easy), prefer_sharps=True)


_NOTE_FULLNAMES = {
    "C": "C", "D": "D", "E": "E", "F": "F", "G": "G", "A": "A", "B": "B",
}
