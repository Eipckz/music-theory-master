"""Spelling-aware note analysis and exact rhythm arithmetic for assignments."""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import re

from .pitch import Note


def analyze_notes(text: str, tonic: str = "C", mode: str = "major") -> tuple[list[int], str]:
    """Analyze supplied notes without inventing missing voices or harmonic context."""
    from music21 import chord, interval, key, pitch, roman

    tokens = text.replace(",", " ").split()
    if not 1 <= len(tokens) <= 64:
        raise ValueError("Enter 1–64 notes separated by spaces or commas.")
    notes = [Note.parse(token) for token in tokens]
    if any(not 0 <= note.midi <= 127 for note in notes):
        raise ValueError("Notes must lie within MIDI 0–127.")
    if mode not in ("major", "minor"):
        raise ValueError("Choose major or minor for the tonal interpretation.")
    if not re.fullmatch(r"[A-Ga-g](?:##|bb|x|#|b|n)?", tonic.strip()):
        raise ValueError("Enter a tonic letter and accidental without an octave, such as C or Bb.")
    tonic_note = Note.parse(tonic)
    context = key.Key(tonic_note.m21_name[:-1], mode)
    lines = [f"Context: {context}. Omitted octaves default to 4; A4 = 440 Hz.", "",
             "Supplied pitches (input order):"]
    for note in notes:
        frequency = 440 * 2 ** ((note.midi - 69) / 12)
        lines.append(f"{note.name}: MIDI {note.midi}, {frequency:.2f} Hz")
    lines.extend(["", "Intervals between adjacent supplied notes:"])
    for first, second in zip(notes, notes[1:]):
        measured = interval.Interval(pitch.Pitch(first.m21_name), pitch.Pitch(second.m21_name))
        direction = "ascending" if second.midi > first.midi else "descending" if second.midi < first.midi else "same pitch"
        lines.append(f"{first.name} → {second.name}: {measured.niceName}, {direction} ({measured.semitones:+g} semitones)")
    if len(notes) == 1:
        lines.append("Add a second note to measure an interval.")
    collection = chord.Chord([note.m21_name for note in notes])
    lines.extend(["", f"Collection: {collection.pitchedCommonName}",
                  f"Bass (lowest supplied pitch): {collection.bass().nameWithOctave}"])
    if len({note.pc for note in notes}) >= 3:
        interpretation = roman.romanNumeralFromChord(collection, context)
        lines.append(f"Possible tonal interpretation: {interpretation.figure} in {context}")
    else:
        lines.append("Fewer than three pitch classes: insufficient information to identify a full chord.")
    lines.extend(["", "Chord labels are interpretations of the supplied spelling and key, not proof of function.",
                  "Missing tones, nonchord tones and musical context may change the analysis.",
                  "Use the Part-writing Lab to check voice-leading between chords."])
    return [note.midi for note in notes], "\n".join(lines)


@dataclass(frozen=True)
class RhythmBar:
    total: Fraction
    capacity: Fraction

    @property
    def remaining(self) -> Fraction:
        return self.capacity - self.total


_VALUES = {"w": Fraction(4), "h": Fraction(2), "q": Fraction(1),
           "e": Fraction(1, 2), "s": Fraction(1, 4), "x": Fraction(1, 8)}


def duration(token: str) -> Fraction:
    """Quarter-note units; dots and 3-in-the-time-of-2 triplets are exact."""
    original = token
    if token.startswith("r"):
        token = token[1:]
    triplet = token.startswith("t(") and token.endswith(")")
    if triplet:
        token = token[2:-1]
    match = re.fullmatch(r"(w|h|q|e|s|x|[1-9][0-9]*/[1-9][0-9]*)(\.{0,2})", token)
    if not match:
        raise ValueError(f"Unknown duration {original!r}. Use q, h., e, rq, t(e), or 1/8.")
    value, dots = match.groups()
    base = _VALUES[value] if value in _VALUES else 4 * Fraction(value)
    return base * sum((Fraction(1, 2**i) for i in range(len(dots) + 1)), Fraction()) * (Fraction(2, 3) if triplet else 1)


def analyze_rhythm(text: str, meter: str = "4/4") -> tuple[list[RhythmBar], str]:
    match = re.fullmatch(r"(\d{1,2})/(1|2|4|8|16|32)", meter.strip())
    if not match or not 1 <= int(match[1]) <= 32:
        raise ValueError("Use a meter with 1–32 upper number and denominator 1, 2, 4, 8, 16 or 32.")
    upper, lower = map(int, match.groups())
    capacity = Fraction(4 * upper, lower)
    if upper in (6, 9, 12):
        pulse = f"Compound meter: normally {upper // 3} beats, each spanning 3 denominator units."
    elif upper in (2, 3, 4):
        pulse = f"Simple meter: normally {upper} beats, each spanning 1 denominator unit."
    else:
        pulse = "Beat grouping depends on the music; specify additive groups separately when performing."
    if not text.strip() or len(text) > 10000:
        raise ValueError("Enter durations (up to 10,000 characters); separate bars with |.")
    bars = []
    lines = [f"Meter: {upper}/{lower}. Bar capacity: {capacity} quarter-note units.", pulse, ""]
    for number, raw in enumerate(text.split("|"), 1):
        if not raw.strip():
            raise ValueError(f"Bar {number} is empty; enter durations on both sides of |.")
        total = sum((duration(token) for token in raw.split()), Fraction())
        bar = RhythmBar(total, capacity)
        bars.append(bar)
        status = "complete" if bar.remaining == 0 else f"short by {bar.remaining}" if bar.remaining > 0 else f"over by {-bar.remaining}"
        lines.append(f"Bar {number}: {total} / {capacity} quarter-note units — {status}")
    lines.extend(["", "A short bar can be intentional (for example, a pickup).",
                  "This checks duration totals, not beaming, accent, tuplet grouping or tie legality."])
    return bars, "\n".join(lines)
