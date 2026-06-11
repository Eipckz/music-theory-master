"""Spelled pitches and intervals.

A :class:`Note` keeps letter + accidental + octave so enharmonic spelling
(C# vs Db) is preserved, which matters for correct interval and scale naming.
MIDI 60 == C4 (scientific pitch notation)."""

from __future__ import annotations

import re
from dataclasses import dataclass

LETTERS = "CDEFGAB"
_LETTER_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
_LETTER_IDX = {ltr: i for i, ltr in enumerate(LETTERS)}

_ACC_TO_ALTER = {"": 0, "n": 0, "#": 1, "x": 2, "##": 2, "b": -1, "bb": -2, "-": -1, "--": -2}
_ALTER_TO_ACC = {-2: "bb", -1: "b", 0: "", 1: "#", 2: "x"}

_NOTE_RE = re.compile(r"^([A-Ga-g])(##|bb|--|x|#|b|-|n)?(-?\d+)?$")

# Quality reference: simple-interval number -> semitones for perfect/major.
_PERFECT_NUMBERS = {1, 4, 5, 8}
_REF_SEMITONES = {1: 0, 2: 2, 3: 4, 4: 5, 5: 7, 6: 9, 7: 11, 8: 12}


@dataclass(frozen=True)
class Note:
    letter: str          # 'C'..'B'
    alter: int = 0       # -2..+2 semitone alteration
    octave: int = 4

    def __post_init__(self) -> None:
        if self.letter not in _LETTER_PC:
            raise ValueError(f"bad letter: {self.letter!r}")
        if not -2 <= self.alter <= 2:
            raise ValueError(f"alter out of range: {self.alter}")

    @property
    def midi(self) -> int:
        return 12 * (self.octave + 1) + _LETTER_PC[self.letter] + self.alter

    @property
    def pc(self) -> int:
        return self.midi % 12

    @property
    def accidental(self) -> str:
        return _ALTER_TO_ACC[self.alter]

    @property
    def name(self) -> str:
        return f"{self.letter}{self.accidental}{self.octave}"

    @property
    def name_no_octave(self) -> str:
        return f"{self.letter}{self.accidental}"

    @property
    def m21_name(self) -> str:
        """Name using music21's accidental spelling ('-' flat, '##' dbl sharp)."""
        acc = {-2: "--", -1: "-", 0: "", 1: "#", 2: "##"}[self.alter]
        return f"{self.letter}{acc}{self.octave}"

    @property
    def diatonic_index(self) -> int:
        """Absolute position on the letter ladder (C0 == 0)."""
        return _LETTER_IDX[self.letter] + 7 * self.octave

    @classmethod
    def parse(cls, text: str) -> "Note":
        m = _NOTE_RE.match(text.strip())
        if not m:
            raise ValueError(f"cannot parse note: {text!r}")
        letter, acc, octv = m.groups()
        letter = letter.upper()
        alter = _ACC_TO_ALTER.get(acc or "", 0)
        octave = int(octv) if octv is not None else 4
        return cls(letter, alter, octave)

    @classmethod
    def from_midi(cls, midi: int, prefer_sharps: bool = True) -> "Note":
        """Spell a MIDI number using sharps or flats for the black keys."""
        pc = midi % 12
        octave = midi // 12 - 1
        sharp_spell = {
            0: ("C", 0), 1: ("C", 1), 2: ("D", 0), 3: ("D", 1), 4: ("E", 0),
            5: ("F", 0), 6: ("F", 1), 7: ("G", 0), 8: ("G", 1), 9: ("A", 0),
            10: ("A", 1), 11: ("B", 0),
        }
        flat_spell = {
            0: ("C", 0), 1: ("D", -1), 2: ("D", 0), 3: ("E", -1), 4: ("E", 0),
            5: ("F", 0), 6: ("G", -1), 7: ("G", 0), 8: ("A", -1), 9: ("A", 0),
            10: ("B", -1), 11: ("B", 0),
        }
        letter, alter = (sharp_spell if prefer_sharps else flat_spell)[pc]
        return cls(letter, alter, octave)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.name


def midi_to_name(midi: int, prefer_sharps: bool = True) -> str:
    return Note.from_midi(midi, prefer_sharps).name


def name_to_midi(name: str) -> int:
    return Note.parse(name).midi


@dataclass(frozen=True)
class Interval:
    number: int          # 1 = unison, 2 = second, ...
    quality: str         # 'P','M','m','A','d','AA','dd'
    semitones: int

    @property
    def name(self) -> str:
        return f"{self.quality}{self.number}"

    @property
    def is_compound(self) -> bool:
        return self.number > 8


def _quality_from_diff(number: int, diff: int) -> str:
    simple = ((number - 1) % 7) + 1
    if simple in _PERFECT_NUMBERS or number == 8:
        table = {0: "P", 1: "A", 2: "AA", -1: "d", -2: "dd"}
    else:
        table = {0: "M", -1: "m", 1: "A", 2: "AA", -2: "d", -3: "dd"}
    return table.get(diff, ("A" * diff if diff > 0 else "d" * (-diff)))


def interval_between(a: Note, b: Note) -> Interval:
    """Directed interval magnitude from a to b (always reported ascending)."""
    lo, hi = (a, b) if b.midi >= a.midi else (b, a)
    dia = hi.diatonic_index - lo.diatonic_index          # generic steps
    number = dia + 1
    semis = hi.midi - lo.midi
    octaves = (number - 1) // 7
    simple_number = ((number - 1) % 7) + 1
    ref = _REF_SEMITONES[simple_number] + 12 * octaves
    diff = semis - ref
    quality = _quality_from_diff(number, diff)
    return Interval(number=number, quality=quality, semitones=semis)


# Semitone span for each (quality, simple-number) used when transposing.
_QUALITY_OFFSET = {
    "P": 0, "M": 0, "m": -1, "A": 1, "d_perf": -1, "d_imperf": -2, "AA": 2, "dd_perf": -2, "dd_imperf": -3,
}


def transpose(note: Note, number: int, quality: str) -> Note:
    """Transpose a note up by a named interval, preserving correct spelling."""
    if number < 1:
        raise ValueError("interval number must be >= 1")
    target_idx = note.diatonic_index + (number - 1)
    new_letter = LETTERS[target_idx % 7]
    new_octave = target_idx // 7
    simple = ((number - 1) % 7) + 1
    perfecty = simple in _PERFECT_NUMBERS or number == 8
    ref = _REF_SEMITONES[simple] + 12 * ((number - 1) // 7)
    if perfecty:
        diff = {"P": 0, "A": 1, "AA": 2, "d": -1, "dd": -2}[quality]
    else:
        diff = {"M": 0, "m": -1, "A": 1, "AA": 2, "d": -2, "dd": -3}[quality]
    target_semis = note.midi + ref + diff
    base_pc = _LETTER_PC[new_letter]
    natural_midi = 12 * (new_octave + 1) + base_pc
    alter = target_semis - natural_midi
    # normalize spelling into octave if rounding pushed us off by 12
    while alter > 2:
        new_octave += 1
        natural_midi = 12 * (new_octave + 1) + base_pc
        alter = target_semis - natural_midi
    while alter < -2:
        new_octave -= 1
        natural_midi = 12 * (new_octave + 1) + base_pc
        alter = target_semis - natural_midi
    return Note(new_letter, alter, new_octave)


def enharmonic_equal(a: Note, b: Note) -> bool:
    return a.midi == b.midi


_SEMITONE_NAMES = {
    0: "P1", 1: "m2", 2: "M2", 3: "m3", 4: "M3", 5: "P4", 6: "TT",
    7: "P5", 8: "m6", 9: "M6", 10: "m7", 11: "M7", 12: "P8",
}


def simple_interval_name(semitones: int) -> str:
    """Interval label from a semitone count (for ear-training answer keys)."""
    if semitones in _SEMITONE_NAMES:
        return _SEMITONE_NAMES[semitones]
    reduced = semitones % 12
    return "P8" if reduced == 0 else _SEMITONE_NAMES[reduced]
