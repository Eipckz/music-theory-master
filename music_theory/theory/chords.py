"""Chords, inversions, figured bass, and roman-numeral analysis.

Triad/seventh construction is implemented directly for speed and deterministic
spelling. Roman-numeral conversion is delegated to music21 (already a
dependency) because correct functional analysis across major/minor, sevenths,
inversions and secondary functions is subtle and music21 is battle-tested."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional, Sequence

from .pitch import Note, transpose
from .scales import scale_notes

# quality -> spelled interval specs (number, quality) measured from the root.
CHORD_QUALITIES: dict[str, list[tuple[int, str]]] = {
    "major":      [(1, "P"), (3, "M"), (5, "P")],
    "minor":      [(1, "P"), (3, "m"), (5, "P")],
    "diminished": [(1, "P"), (3, "m"), (5, "d")],
    "augmented":  [(1, "P"), (3, "M"), (5, "A")],
    "maj7":       [(1, "P"), (3, "M"), (5, "P"), (7, "M")],
    "dom7":       [(1, "P"), (3, "M"), (5, "P"), (7, "m")],
    "min7":       [(1, "P"), (3, "m"), (5, "P"), (7, "m")],
    "halfdim7":   [(1, "P"), (3, "m"), (5, "d"), (7, "m")],
    "dim7":       [(1, "P"), (3, "m"), (5, "d"), (7, "d")],
    "minMaj7":    [(1, "P"), (3, "m"), (5, "P"), (7, "M")],
    "augMaj7":    [(1, "P"), (3, "M"), (5, "A"), (7, "M")],
    "dom7b5":     [(1, "P"), (3, "M"), (5, "d"), (7, "m")],
}

TRIAD_QUALITIES = ["major", "minor", "diminished", "augmented"]
SEVENTH_QUALITIES = ["maj7", "dom7", "min7", "halfdim7", "dim7", "minMaj7"]

QUALITY_SYMBOL = {
    "major": "", "minor": "m", "diminished": "dim", "augmented": "aug",
    "maj7": "maj7", "dom7": "7", "min7": "m7", "halfdim7": "\u00f87",
    "dim7": "\u00b07", "minMaj7": "m(maj7)", "augMaj7": "aug(maj7)", "dom7b5": "7b5",
}


@dataclass
class Chord:
    root: Note
    quality: str
    members: list[Note] = field(default_factory=list)
    inversion: int = 0

    @property
    def is_seventh(self) -> bool:
        return len(self.members) >= 4

    @property
    def pcs(self) -> list[int]:
        return [n.pc for n in self.members]

    @property
    def symbol(self) -> str:
        return f"{self.root.name_no_octave}{QUALITY_SYMBOL.get(self.quality, self.quality)}"

    @property
    def bass(self) -> Note:
        return self.members[self.inversion % len(self.members)]

    def voiced(self, low_octave: int = 3) -> list[Note]:
        """Return notes stacked upward from the bass for the current inversion."""
        n = len(self.members)
        order = [self.members[(self.inversion + i) % n] for i in range(n)]
        out: list[Note] = []
        prev_midi = Note(order[0].letter, order[0].alter, low_octave).midi
        out.append(Note(order[0].letter, order[0].alter, low_octave))
        for note in order[1:]:
            octave = low_octave
            cand = Note(note.letter, note.alter, octave)
            while cand.midi <= prev_midi:
                octave += 1
                cand = Note(note.letter, note.alter, octave)
            out.append(cand)
            prev_midi = cand.midi
        return out

    @property
    def figured_bass(self) -> str:
        return figured_bass(self.is_seventh, self.inversion)


def _build(root: Note, quality: str) -> Chord:
    specs = CHORD_QUALITIES[quality]
    members = [transpose(root, num, q) for num, q in specs]
    return Chord(root=root, quality=quality, members=members)


def triad(root: Note, quality: str = "major") -> Chord:
    if quality not in ("major", "minor", "diminished", "augmented"):
        raise ValueError(f"not a triad quality: {quality}")
    return _build(root, quality)


def seventh(root: Note, quality: str = "dom7") -> Chord:
    if quality not in CHORD_QUALITIES or len(CHORD_QUALITIES[quality]) != 4:
        raise ValueError(f"not a seventh quality: {quality}")
    return _build(root, quality)


def figured_bass(is_seventh: bool, inversion: int) -> str:
    if is_seventh:
        return {0: "7", 1: "65", 2: "43", 3: "42"}.get(inversion, "7")
    return {0: "", 1: "6", 2: "64"}.get(inversion, "")


def identify_chord(notes: Sequence[Note]) -> Optional[dict]:
    """Determine root, quality and inversion from a set of spelled notes."""
    if len(notes) < 3:
        return None
    by_pc: dict[int, Note] = {}
    for n in notes:
        by_pc.setdefault(n.pc, n)
    uniq = list(by_pc.values())
    bass = min(notes, key=lambda n: n.midi)
    for root in uniq:
        for quality, specs in CHORD_QUALITIES.items():
            if len(specs) != len(uniq):
                continue
            target = {transpose(root, num, q).pc for num, q in specs}
            if target == {n.pc for n in uniq}:
                members = [transpose(root, num, q) for num, q in specs]
                inv = next((i for i, m in enumerate(members) if m.pc == bass.pc), 0)
                return {
                    "root": root, "quality": quality, "inversion": inv,
                    "figured_bass": figured_bass(len(specs) == 4, inv),
                }
    return None


# ----------------------------------------------------------------------------
# Roman numerals via music21 (lazy import - keeps theory import light/offline).
# ----------------------------------------------------------------------------
def _m21():
    import music21  # noqa: WPS433 - deferred, optional heavy dependency
    return music21


def _to_m21_tonic(name: str) -> str:
    """Translate app key spelling (``Gb``, ``Bb``) to music21's (``G-``, ``B-``)."""
    if len(name) >= 2 and name[1] == "b":
        return name[0] + "-" + name[2:]
    return name


@lru_cache(maxsize=512)
def _m21_key(tonic_name: str, mode: str):
    return _m21().key.Key(_to_m21_tonic(tonic_name), "minor" if "min" in mode else "major")


def _safe_note(pitch) -> Note:
    """Convert a music21 pitch to our :class:`Note`, respelling enharmonically
    when a remote key produces a triple+ accidental our model rejects."""
    try:
        return Note.parse(pitch.nameWithOctave)
    except (ValueError, KeyError):
        return Note.from_midi(int(round(float(pitch.ps))))


def roman_to_chord(figure: str, key_tonic: str = "C", mode: str = "major") -> Chord:
    """Build a Chord from a roman-numeral figure in a key (e.g. 'V65', 'V/V').

    Prefers music21 (battle-tested functional analysis), but is fully
    crash-proof: out-of-range enharmonic spellings are respelled, and if
    music21 is unavailable (e.g. a trimmed frozen build) a self-contained
    diatonic engine takes over."""
    try:
        return _roman_via_m21(figure, key_tonic, mode)
    except Exception:  # noqa: BLE001 - any music21 failure -> pure-python path
        return _diatonic_roman_to_chord(figure, key_tonic, mode)


def _roman_via_m21(figure: str, key_tonic: str, mode: str) -> Chord:
    m21 = _m21()
    rn = m21.roman.RomanNumeral(figure, _m21_key(key_tonic, mode))
    notes = [_safe_note(p) for p in rn.pitches]
    if not notes:
        raise ValueError(f"empty roman numeral: {figure!r}")
    root = _safe_note(rn.root())
    info = identify_chord(notes)
    quality = info["quality"] if info else _quality_from_m21(rn)
    members_sorted = _root_position(root, notes)
    bass_pc = min(notes, key=lambda n: n.midi).pc
    inv = next((i for i, m in enumerate(members_sorted) if m.pc == bass_pc), 0)
    return Chord(root=root, quality=quality, members=members_sorted, inversion=inv)


# ----------------------------------------------------------------------------
# Pure-python diatonic roman numerals (music21-free fallback).
# Correct for the full set of figures the app generates: diatonic triads and
# sevenths in major/minor, inversions (6, 64, 7, 65, 43, 42), and applied
# chords (e.g. V/V, vii\u00b0/vi).
# ----------------------------------------------------------------------------
_ROMAN_NUM = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7}
_ROMAN_RE = re.compile(r"^([#b\-]*)([iIvV]+)([o\u00b0\u00f8+]*)(\d*)$")
_SEVENTH_FIGS = {"7": 0, "65": 1, "43": 2, "42": 3}
_TRIAD_FIGS = {"": 0, "6": 1, "64": 2}


def _scale_degree_root(key_tonic: str, mode: str, degree: int, acc: str,
                       raised_lt: bool = False) -> Note:
    tonic = Note.parse(key_tonic + "4")
    stype = "major" if mode == "major" else "natural_minor"
    notes = scale_notes(tonic, stype, octaves=1)
    root = notes[(degree - 1) % 7]
    if mode != "major" and degree == 7 and raised_lt:
        root = transpose(root, 1, "A")  # raise the leading tone for vii\u00b0/V
    if acc:
        alter = root.alter + acc.count("#") - acc.count("b") - acc.count("-")
        root = Note(root.letter, max(-2, min(2, alter)), root.octave)
    return root


def _roman_quality(roman: str, marks: str, is_seventh: bool, degree: int) -> str:
    upper = roman.isupper()
    if "o" in marks or "\u00b0" in marks:
        return "dim7" if is_seventh else "diminished"
    if "\u00f8" in marks:
        return "halfdim7"
    if "+" in marks:
        return "augmented"
    if is_seventh:
        if upper:
            return "dom7" if degree == 5 else "maj7"
        return "min7"
    return "major" if upper else "minor"


def _diatonic_roman_to_chord(figure: str, key_tonic: str = "C", mode: str = "major") -> Chord:
    fig = figure.strip()
    if "/" in fig:
        left, right = fig.split("/", 1)
        rm = _ROMAN_RE.match(right.strip().replace("\u00b0", "o"))
        if not rm:
            raise ValueError(f"cannot parse applied target: {right!r}")
        target = _scale_degree_root(key_tonic, mode, _ROMAN_NUM[rm.group(2).lower()],
                                    rm.group(1), raised_lt=False)
        temp_mode = "major" if rm.group(2).isupper() else "minor"
        return _diatonic_roman_to_chord(left, target.name_no_octave, temp_mode)

    m = _ROMAN_RE.match(fig.replace("\u00b0", "o"))
    if not m:
        raise ValueError(f"cannot parse roman numeral: {figure!r}")
    acc, roman, marks, digits = m.groups()
    if roman.lower() not in _ROMAN_NUM:
        raise ValueError(f"unknown roman numeral: {roman!r}")
    degree = _ROMAN_NUM[roman.lower()]
    is_seventh = digits in _SEVENTH_FIGS
    inversion = _SEVENTH_FIGS[digits] if is_seventh else _TRIAD_FIGS.get(digits, 0)
    quality = _roman_quality(roman, marks, is_seventh, degree)
    root = _scale_degree_root(key_tonic, mode, degree, acc,
                              raised_lt=("o" in marks or "\u00b0" in marks))
    ch = seventh(root, quality) if is_seventh else triad(root, quality)
    ch.inversion = inversion
    return ch


def _root_position(root: Note, members: Sequence[Note]) -> list[Note]:
    by_pc = {m.pc: m for m in members}
    ordered = sorted(by_pc.values(), key=lambda n: (n.pc - root.pc) % 12)
    return ordered


def _quality_from_m21(rn) -> str:
    q = rn.quality  # 'major','minor','diminished','augmented'
    if rn.isSeventh() if hasattr(rn, "isSeventh") else len(rn.pitches) == 4:
        mapping = {
            "major": "maj7", "minor": "min7", "diminished": "dim7",
            "dominant": "dom7", "augmented": "augMaj7", "half-diminished": "halfdim7",
        }
        return mapping.get(getattr(rn, "commonName", ""), "dom7")
    return {"major": "major", "minor": "minor", "diminished": "diminished",
            "augmented": "augmented"}.get(q, "major")


def chord_to_roman(notes: Sequence[Note], key_tonic: str = "C", mode: str = "major") -> str:
    """Return the roman-numeral figure for a chord in a key."""
    m21 = _m21()
    chord = m21.chord.Chord([p.m21_name for p in notes])
    rn = m21.roman.romanNumeralFromChord(chord, _m21_key(key_tonic, mode))
    return rn.figure
