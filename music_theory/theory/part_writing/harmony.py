"""Harmony normalization, functional grammar, and chromatic spellings."""

from __future__ import annotations

import re
import copy
from dataclasses import dataclass
from functools import lru_cache

from ..chords import Chord, identify_chord, roman_to_chord, seventh, triad
from ..pitch import Note
from ..scales import scale_notes
from .models import (
    CadenceType, ChordFactor, HarmonyConstraint, PartWritingProblem,
)


_FACTOR_ORDER = (ChordFactor.ROOT, ChordFactor.THIRD,
                 ChordFactor.FIFTH, ChordFactor.SEVENTH)
_SYMBOL_RE = re.compile(
    r"^([A-Ga-g])((?:bb|##|b|#|x)?)(maj7|m7|dim7|o7|ø7|hdim7|7|dim|o|aug|\+|m)?(?:/(.+))?$"
)
_FIGURE_TO_INVERSION = {"": 0, "53": 0, "5/3": 0, "6": 1,
                        "63": 1, "6/3": 1, "64": 2, "6/4": 2,
                        "7": 0, "65": 1, "6/5": 1, "43": 2,
                        "4/3": 2, "42": 3, "4/2": 3, "2": 3}


@dataclass(frozen=True)
class NormalizedHarmony:
    label: str
    chord: Chord
    factors: tuple[ChordFactor, ...]
    inversion: int
    special: str = ""
    applied_target_pc: int | None = None

    @property
    def members(self) -> tuple[Note, ...]:
        return tuple(self.chord.members)

    @property
    def pcs(self) -> tuple[int, ...]:
        return tuple(note.pc for note in self.members)

    @property
    def bass_factor(self) -> ChordFactor:
        return self.factors[self.inversion]

    def factor_for(self, note: Note) -> ChordFactor | None:
        for factor, member in zip(self.factors, self.members):
            if note.pc == member.pc and note.letter == member.letter:
                return factor
        for factor, member in zip(self.factors, self.members):
            if note.pc == member.pc:
                return factor
        return None

    def member_for(self, factor: ChordFactor) -> Note | None:
        try:
            return self.members[self.factors.index(factor)]
        except (ValueError, IndexError):
            return None


def _with_octave(note: Note, octave: int = 4) -> Note:
    return Note(note.letter, note.alter, octave)


def _degree(key_tonic: str, mode: str, degree: int, alteration: int = 0) -> Note:
    tonic = Note.parse(key_tonic + "4")
    scale_type = "major" if mode == "major" else "natural_minor"
    note = scale_notes(tonic, scale_type)[degree - 1]
    return Note(note.letter, note.alter + alteration, 4)


def _special_harmony(label: str, key_tonic: str, mode: str) -> NormalizedHarmony | None:
    compact = label.replace(" ", "").replace("♭", "b").replace("♯", "#")
    if compact.upper() in {"N6", "BII6"}:
        root = _degree(key_tonic, mode, 2, -1)
        chord = triad(root, "major")
        chord.inversion = 1
        return NormalizedHarmony("N6", chord, _FACTOR_ORDER[:3], 1, "neapolitan")

    if compact.lower() in {"it+6", "italian+6", "it6"}:
        tonic = _degree(key_tonic, mode, 1)
        # Natural minor already contains lowered scale degree 6; applying an
        # additional flat would misspell the directed tone (Abb in C minor).
        low = _degree(key_tonic, mode, 6, -1 if mode == "major" else 0)
        raised_four = _degree(key_tonic, mode, 4, 1)
        chord = Chord(low, "italian+6", [low, tonic, raised_four], inversion=0)
        return NormalizedHarmony("It+6", chord, _FACTOR_ORDER[:3], 0, "augmented-sixth")
    if compact.lower() in {"fr+6", "french+6", "fr6"}:
        low = _degree(key_tonic, mode, 6, -1 if mode == "major" else 0)
        tonic = _degree(key_tonic, mode, 1)
        two = _degree(key_tonic, mode, 2)
        raised_four = _degree(key_tonic, mode, 4, 1)
        chord = Chord(low, "french+6", [low, tonic, two, raised_four], inversion=0)
        return NormalizedHarmony("Fr+6", chord, _FACTOR_ORDER, 0, "augmented-sixth")
    if compact.lower() in {"ger+6", "german+6", "ger6"}:
        low = _degree(key_tonic, mode, 6, -1 if mode == "major" else 0)
        tonic = _degree(key_tonic, mode, 1)
        flat_three = _degree(key_tonic, mode, 3, -1 if mode == "major" else 0)
        raised_four = _degree(key_tonic, mode, 4, 1)
        chord = Chord(low, "german+6", [low, tonic, flat_three, raised_four], inversion=0)
        return NormalizedHarmony("Ger+6", chord, _FACTOR_ORDER, 0, "augmented-sixth")
    return None


def chord_symbol_to_chord(symbol: str) -> Chord:
    symbol = symbol.strip().replace("♭", "b").replace("♯", "#")
    if symbol.lower().startswith("notes:"):
        names = symbol[6:].replace(",", " ").split()
        members = [Note.parse(name + "4") for name in names]
        if not 2 <= len(members) <= 7 or len({n.pc for n in members}) != len(members):
            raise ValueError("Custom chords need 2–7 distinct pitch classes, root first: notes:C E G Bb")
        if len({n.letter for n in members}) != len(members):
            raise ValueError("Use distinct letter names for custom chord factors.")
        return Chord(members[0], "custom", members, inversion=0)
    match = _SYMBOL_RE.match(symbol.strip())
    if not match:
        # music21 is bundled and works entirely offline. Keep the small parser
        # for familiar symbols and use this for sus/add/altered/extended chords.
        try:
            from music21 import harmony as m21h
            from ..chords import _safe_note
            figure = re.sub(r"^([A-G])b", r"\1-", symbol)
            figure = re.sub(r"/([A-G])b", r"/\1-", figure)
            parsed = m21h.ChordSymbol(figure)
            root = _safe_note(parsed.root())
            members = sorted((_safe_note(p) for p in parsed.pitches),
                             key=lambda n: (n.diatonic_index - root.diatonic_index) % 7)
            if not 2 <= len(members) <= 7:
                raise ValueError("Expected 2–7 chord members")
            bass = _safe_note(parsed.bass())
            inv = next(i for i, n in enumerate(members) if n.pc == bass.pc)
            return Chord(root, "extended", members, inversion=inv)
        except Exception as exc:
            raise ValueError(f"Cannot read chord {symbol!r}. Try a chord symbol or notes:C E G Bb.") from exc
    letter, accidental, suffix, bass_name = match.groups()
    root = Note.parse(letter.upper() + accidental + "4")
    suffix = suffix or ""
    quality = {
        "": "major", "m": "minor", "dim": "diminished", "o": "diminished",
        "aug": "augmented", "+": "augmented", "7": "dom7", "maj7": "maj7",
        "m7": "min7", "dim7": "dim7", "o7": "dim7", "ø7": "halfdim7",
        "hdim7": "halfdim7",
    }[suffix]
    chord = seventh(root, quality) if quality.endswith("7") else triad(root, quality)
    if bass_name:
        bass = Note.parse(bass_name + "4")
        inversion = next((i for i, member in enumerate(chord.members)
                          if member.pc == bass.pc), None)
        if inversion is None:
            raise ValueError(f"Slash bass {bass_name!r} is not a chord member")
        chord.inversion = inversion
    return chord


def _factor_tuple(chord: Chord) -> tuple[ChordFactor, ...]:
    degrees = (ChordFactor.ROOT, ChordFactor.SECOND, ChordFactor.THIRD,
               ChordFactor.FOURTH, ChordFactor.FIFTH, ChordFactor.SIXTH,
               ChordFactor.SEVENTH)
    return tuple(degrees[(n.diatonic_index - chord.root.diatonic_index) % 7]
                 for n in chord.members)


def _same_harmony(left: Chord, right: Chord) -> bool:
    return ({n.pc for n in left.members} == {n.pc for n in right.members}
            and left.inversion == right.inversion)


@lru_cache(maxsize=2048)
def _roman_cached(label: str, key: str, mode: str) -> Chord:
    return roman_to_chord(label, key, mode)


def normalize_constraint(constraint: HarmonyConstraint, key_tonic: str,
                         mode: str) -> NormalizedHarmony:
    roman = (constraint.roman_numeral or "").strip()
    symbol = (constraint.chord_symbol or "").strip()
    special = _special_harmony(roman or symbol, key_tonic, mode)
    roman_chord = None
    symbol_chord = None
    if special is not None:
        chord = special.chord
        label = special.label
    else:
        if roman:
            roman_chord = copy.deepcopy(_roman_cached(roman.replace("°", "o"), key_tonic, mode))
        if symbol:
            symbol_chord = chord_symbol_to_chord(symbol)
        if roman_chord is not None and symbol_chord is not None \
                and not _same_harmony(roman_chord, symbol_chord):
            raise ValueError(
                f"Roman numeral {roman!r} and chord symbol {symbol!r} describe different harmonies"
            )
        chord = roman_chord or symbol_chord
        if chord is None:
            raise ValueError("A harmony label is required for normalization")
        label = roman or symbol

    figure = (constraint.figured_bass or "").replace(" ", "")
    if figure:
        if figure not in _FIGURE_TO_INVERSION:
            raise ValueError(f"Unsupported figured-bass symbol: {constraint.figured_bass!r}")
        figured_inversion = _FIGURE_TO_INVERSION[figure]
        if figured_inversion >= len(chord.members):
            raise ValueError(f"Figure {figure!r} is incompatible with {label!r}")
        if (roman or symbol) and chord.inversion not in (0, figured_inversion):
            raise ValueError(f"Figure {figure!r} conflicts with {label!r}")
        chord.inversion = figured_inversion
    if constraint.inversion is not None:
        inv = int(constraint.inversion)
        if not 0 <= inv < len(chord.members):
            raise ValueError(f"Inversion {inv} is incompatible with {label!r}")
        if figure and inv != chord.inversion:
            raise ValueError("Explicit inversion and figured bass conflict")
        chord.inversion = inv

    applied_target_pc = None
    if "/" in roman:
        target = roman.split("/", 1)[1]
        try:
            target_chord = roman_to_chord(target, key_tonic, mode)
            applied_target_pc = target_chord.root.pc
        except Exception:  # the label itself remains usable through the main parser
            applied_target_pc = None
    elif symbol and not roman and chord.quality == "dom7":
        applied_target_pc = (chord.root.pc + 5) % 12
    return NormalizedHarmony(label, chord, special.factors if special else _factor_tuple(chord), chord.inversion,
                             special.special if special else "", applied_target_pc)


def harmonies_for_slot(problem: PartWritingProblem, slot_index: int) -> list[NormalizedHarmony]:
    slot = problem.slots[slot_index]
    constraint = slot.harmony
    labels: list[str] = []
    forbidden = {label.strip().lower() for label in constraint.forbidden_harmonies}
    if constraint.roman_numeral or constraint.chord_symbol:
        normalized = normalize_constraint(constraint, problem.key_tonic, problem.mode)
        return [] if normalized.label.strip().lower() in forbidden else [normalized]
    labels.extend(constraint.allowed_harmonies)
    if not labels:
        labels = functional_candidates(problem, slot_index)
    out = []
    for label in labels:
        is_symbol = bool(re.match(r"^[A-Ga-g](?:[#b]|maj|min|dim|aug|sus|add|m|\d|/|$)", label)) or label.lower().startswith("notes:")
        temp = HarmonyConstraint(
            roman_numeral=None if is_symbol else label,
            chord_symbol=label if is_symbol else None,
            figured_bass=constraint.figured_bass,
            inversion=constraint.inversion,
            exact_bass_pitch=constraint.exact_bass_pitch,
            required_chord_tones=constraint.required_chord_tones,
            forbidden_chord_tones=constraint.forbidden_chord_tones,
            required_doubling=constraint.required_doubling,
            forbidden_harmonies=constraint.forbidden_harmonies,
        )
        try:
            normalized = normalize_constraint(temp, problem.key_tonic, problem.mode)
            if normalized.label.strip().lower() not in forbidden:
                out.append(normalized)
        except ValueError:
            continue
    return out


def functional_candidates(problem: PartWritingProblem, slot_index: int) -> list[str]:
    """Small deterministic grammar used only to fill genuinely blank harmony."""
    last = len(problem.slots) - 1
    if problem.cadence and slot_index == last:
        if problem.cadence == CadenceType.HALF:
            return ["V"]
        if problem.cadence == CadenceType.DECEPTIVE:
            return ["vi" if problem.mode == "major" else "VI"]
        return ["I" if problem.mode == "major" else "i"]
    if problem.cadence and slot_index == last - 1:
        if problem.cadence == CadenceType.PLAGAL:
            return ["IV" if problem.mode == "major" else "iv"]
        return ["V", "V7"]
    # Assignment clues, not column position, determine the harmony. Include
    # inversions so a given bass/figure can identify a chord in any column.
    triads = (["I", "ii", "iii", "IV", "V", "vi", "viio"] if problem.mode == "major"
              else ["i", "iio", "III", "iv", "V", "VI", "viio", "VII", "v"])
    sevenths = (["I", "ii", "iii", "IV", "V", "vi", "viiø"] if problem.mode == "major"
                else ["i", "iiø", "III", "iv", "V", "VI", "viio", "VII"])
    figure = (problem.slots[slot_index].harmony.figured_bass or "").replace("/", "")
    if figure in {"7", "65", "43", "42", "2"}:
        return [label + figure for label in sevenths]
    if figure in {"6", "63", "64", "53"}:
        suffix = {"63": "6", "53": ""}.get(figure, figure)
        return [label + suffix for label in triads]
    return ([label + inv for label in triads for inv in ("", "6", "64")]
            + [label + inv for label in sevenths for inv in ("7", "65", "43", "42")])


def infer_harmony(notes: list[Note], key_tonic: str, mode: str) -> str:
    info = identify_chord(notes)
    if info is None:
        return "Unknown sonority"
    chord = Chord(info["root"], info["quality"], [], info["inversion"])
    try:
        from ..chords import chord_to_roman
        return chord_to_roman(notes, key_tonic, mode)
    except Exception:  # noqa: BLE001 - display fallback remains useful offline
        return f"{chord.root.name_no_octave} {chord.quality}"


def temporary_leading_tone_pc(harmony: NormalizedHarmony, key_tonic: str,
                              mode: str) -> int | None:
    if harmony.applied_target_pc is not None:
        return (harmony.applied_target_pc - 1) % 12
    tonic = Note.parse(key_tonic + "4")
    return (tonic.pc - 1) % 12


def tonic_pc(key_tonic: str) -> int:
    return Note.parse(key_tonic + "4").pc


def scale_degree(note: Note, key_tonic: str, mode: str) -> int | None:
    scale_type = "major" if mode == "major" else "natural_minor"
    for index, member in enumerate(scale_notes(Note.parse(key_tonic + "4"), scale_type), start=1):
        if member.pc == note.pc:
            return index
    return None


def note_for_factor(member: Note, midi: int) -> Note:
    """Place a correctly spelled member at the octave containing ``midi``."""
    octave = midi // 12 - 1
    note = _with_octave(member, octave)
    if note.midi != midi:
        # B# and Cb-style spellings can belong to the adjacent written octave.
        for candidate_octave in (octave - 1, octave + 1):
            candidate = _with_octave(member, candidate_octave)
            if candidate.midi == midi:
                return candidate
    return note
