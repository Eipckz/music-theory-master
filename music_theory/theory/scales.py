"""Scales and key signatures with correct diatonic spelling."""

from __future__ import annotations

from dataclasses import dataclass

from .pitch import LETTERS, Note, _LETTER_IDX, _LETTER_PC

# Semitone offsets from the tonic (ascending, within one octave).
SCALE_TYPES: dict[str, list[int]] = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "natural_minor": [0, 2, 3, 5, 7, 8, 10],
    "harmonic_minor": [0, 2, 3, 5, 7, 8, 11],
    "melodic_minor": [0, 2, 3, 5, 7, 9, 11],
    "ionian": [0, 2, 4, 5, 7, 9, 11],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "phrygian": [0, 1, 3, 5, 7, 8, 10],
    "lydian": [0, 2, 4, 6, 7, 9, 11],
    "mixolydian": [0, 2, 4, 5, 7, 9, 10],
    "aeolian": [0, 2, 3, 5, 7, 8, 10],
    "locrian": [0, 1, 3, 5, 6, 8, 10],
    "major_pentatonic": [0, 2, 4, 7, 9],
    "minor_pentatonic": [0, 3, 5, 7, 10],
    "blues": [0, 3, 5, 6, 7, 10],
    "whole_tone": [0, 2, 4, 6, 8, 10],
    "octatonic_hw": [0, 1, 3, 4, 6, 7, 9, 10],
    "octatonic_wh": [0, 2, 3, 5, 6, 8, 9, 11],
    "chromatic": list(range(12)),
}

_DIATONIC_7 = {
    "major", "natural_minor", "harmonic_minor", "melodic_minor",
    "ionian", "dorian", "phrygian", "lydian", "mixolydian", "aeolian", "locrian",
}

# fifths position of the natural letters (C = 0).
_BASE_FIFTHS = {"F": -1, "C": 0, "G": 1, "D": 2, "A": 3, "E": 4, "B": 5}
_SHARP_ORDER = ["F", "C", "G", "D", "A", "E", "B"]
_FLAT_ORDER = ["B", "E", "A", "D", "G", "C", "F"]


@dataclass(frozen=True)
class Scale:
    tonic: Note
    scale_type: str

    @property
    def notes(self) -> list[Note]:
        return scale_notes(self.tonic, self.scale_type)

    @property
    def pcs(self) -> list[int]:
        return [(self.tonic.pc + off) % 12 for off in SCALE_TYPES[self.scale_type]]

    def degree(self, n: int) -> Note:
        """1-based scale degree."""
        return self.notes[(n - 1) % len(self.notes)]


def _spell_diatonic(tonic: Note, offsets: list[int]) -> list[Note]:
    out: list[Note] = []
    base_idx = _LETTER_IDX[tonic.letter]
    for i, off in enumerate(offsets):
        idx = base_idx + i
        letter = LETTERS[idx % 7]
        octave = tonic.octave + idx // 7
        natural_midi = 12 * (octave + 1) + _LETTER_PC[letter]
        target_midi = tonic.midi + off
        alter = target_midi - natural_midi
        while alter > 2:
            octave += 1
            natural_midi = 12 * (octave + 1) + _LETTER_PC[letter]
            alter = target_midi - natural_midi
        while alter < -2:
            octave -= 1
            natural_midi = 12 * (octave + 1) + _LETTER_PC[letter]
            alter = target_midi - natural_midi
        out.append(Note(letter, alter, octave))
    return out


def scale_notes(tonic: Note, scale_type: str, octaves: int = 1) -> list[Note]:
    if scale_type not in SCALE_TYPES:
        raise ValueError(f"unknown scale type: {scale_type}")
    offsets = SCALE_TYPES[scale_type]
    if scale_type in _DIATONIC_7:
        base = _spell_diatonic(tonic, offsets)
    else:
        prefer_sharps = tonic.alter >= 0 and tonic.letter not in ("F",)
        base = [Note.from_midi(tonic.midi + off, prefer_sharps) for off in offsets]
    result = list(base)
    for o in range(1, octaves):
        result.extend(Note(n.letter, n.alter, n.octave + o) for n in base)
    return result


def key_fifths(tonic: Note, mode: str = "major") -> int:
    f = _BASE_FIFTHS[tonic.letter] + 7 * tonic.alter
    if mode in ("minor", "natural_minor", "harmonic_minor", "melodic_minor", "aeolian"):
        f -= 3
    return f


def key_signature(tonic: Note, mode: str = "major") -> dict:
    """Return number/kind of accidentals and the affected letters."""
    f = key_fifths(tonic, mode)
    if f > 0:
        return {"count": f, "kind": "sharp", "letters": _SHARP_ORDER[:f], "fifths": f}
    if f < 0:
        return {"count": -f, "kind": "flat", "letters": _FLAT_ORDER[:-f], "fifths": f}
    return {"count": 0, "kind": "natural", "letters": [], "fifths": 0}


# Common usable keys (within reasonable accidental counts) for exercises.
def _make_keys() -> dict[str, Note]:
    keys: dict[str, Note] = {}
    majors = ["C", "G", "D", "A", "E", "B", "F#", "C#", "F", "Bb", "Eb", "Ab", "Db", "Gb"]
    for spec in majors:
        keys[spec + " major"] = Note.parse(spec + "4")
    minors = ["A", "E", "B", "F#", "C#", "G#", "D#", "D", "G", "C", "F", "Bb", "Eb", "Ab"]
    for spec in minors:
        keys[spec + " minor"] = Note.parse(spec + "4")
    return keys


KEYS = _make_keys()
