"""Offline practice utilities. Pure calculations are separate from Qt/audio."""
from __future__ import annotations

from dataclasses import dataclass
from html import escape
from pathlib import Path
import random
import re
import statistics

from .pitch import Note
from .scales import SCALE_TYPES, scale_notes


def parse_notes(text: str, maximum: int = 128) -> list[Note]:
    tokens = text.replace(",", " ").split()
    if not 1 <= len(tokens) <= maximum:
        raise ValueError(f"Enter 1–{maximum} spelled notes separated by spaces.")
    notes = [Note.parse(t.replace("♭", "b").replace("♯", "#")) for t in tokens]
    if any(not 0 <= n.midi <= 127 for n in notes):
        raise ValueError("Every note must be in MIDI range 0–127.")
    return notes


INSTRUMENTS = {"Concert pitch": "P1", "Bb clarinet / trumpet": "M-2",
               "A clarinet": "m-3", "F horn": "P-5", "Eb alto sax": "M-6",
               "Bb tenor sax": "M-9", "Guitar (octave)": "P-8"}


def transpose_notes(text: str, size: str, descending: bool = False) -> list[Note]:
    from music21 import interval, pitch
    if not re.fullmatch(r"(?:P|M|m|A|d)(?:[1-9]|1[0-5])", size):
        raise ValueError("Use a spelled interval P1–P15, M/m, A or d, such as M2 or P5.")
    try:
        shift = interval.Interval(size)
        if descending:
            shift = shift.reverse()
        result = []
        for n in parse_notes(text):
            p = pitch.Pitch(n.m21_name).transpose(shift)
            result.append(Note(p.step, int(p.accidental.alter) if p.accidental else 0, p.octave))
    except Exception as exc:
        raise ValueError(f"Cannot represent this transposition: {exc}") from exc
    if any(not 0 <= n.midi <= 127 for n in result):
        raise ValueError("Transposition leaves the supported MIDI range.")
    return result


def instrument_interval(instrument: str, to_concert: bool) -> tuple[str, bool]:
    spec = INSTRUMENTS[instrument]
    return spec.replace("-", ""), ("-" in spec) == to_concert


def export_melody(path: Path, notes: list[Note], title: str = "Transposed melody") -> None:
    from music21 import metadata, note, stream
    score = stream.Score()
    score.metadata = metadata.Metadata(title=title)
    part = stream.Part()
    for n in notes:
        part.append(note.Note(n.m21_name, quarterLength=1))
    score.append(part)
    score.write("musicxml", fp=str(path))


@dataclass(frozen=True)
class ScaleMatch:
    tonic: str
    kind: str
    notes: tuple[Note, ...]
    missing: tuple[int, ...]
    outside: tuple[int, ...]


def find_scales(text: str, tonic: str = "", allow_outside: int = 0) -> list[ScaleMatch]:
    pcs = {n.pc for n in parse_notes(text)}
    if allow_outside not in (0, 1, 2):
        raise ValueError("Allow 0, 1 or 2 outside pitch classes.")
    if tonic.strip() and not re.fullmatch(r"[A-Ga-g](?:##|bb|x|#|b|n)?", tonic.strip()):
        raise ValueError("The optional tonic is a note name without octave, such as C or Bb.")
    roots = parse_notes(tonic, 1) if tonic.strip() else [Note.parse(n) for n in
             ("C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B")]
    results = []
    for root in roots:
        for kind in SCALE_TYPES:
            if kind in ("ionian", "aeolian"):
                continue  # aliases of major and natural minor
            try:
                notes = tuple(scale_notes(root, kind))
            except ValueError:
                continue  # an extreme tonic may require unsupported triple accidentals
            scale_pcs = {n.pc for n in notes}
            outside = tuple(sorted(pcs - scale_pcs))
            if len(outside) <= allow_outside:
                results.append(ScaleMatch(root.name_no_octave, kind, notes,
                                         tuple(sorted(scale_pcs - pcs)), outside))
    return sorted(results, key=lambda s: (len(s.outside), len(s.missing), s.tonic, s.kind))


def metronome_events(bpm: int, groups: str, subdivisions: int, bars: int) -> list[dict]:
    if not 20 <= bpm <= 300 or subdivisions not in (1, 2, 3, 4) or not 1 <= bars <= 32:
        raise ValueError("Use 20–300 BPM, 1–4 subdivisions and 1–32 bars.")
    if not re.fullmatch(r"[1-9](?:\+[1-9]){0,7}", groups):
        raise ValueError("Beat groups must look like 4, 3 or 2+3; each number is 1–9.")
    counts = [int(x) for x in groups.split("+")]
    beats = sum(counts)
    if beats > 16:
        raise ValueError("Use no more than 16 beats per bar.")
    if bars * beats * 60 / bpm > 180:
        raise ValueError("Limit each practice run to three minutes; reduce the bar count.")
    accents = {sum(counts[:i]) for i in range(len(counts))}
    step = 60 / bpm / subdivisions
    result = []
    for i in range(bars * beats * subdivisions):
        beat, sub = divmod(i, subdivisions)
        downbeat = beat % beats == 0 and sub == 0
        accent = beat % beats in accents and sub == 0
        result.append({"start": i * step, "dur": min(.055, step * .5),
                       "midi": 88 if downbeat else 82 if accent else 76 if sub == 0 else 69,
                       "vel": 112 if downbeat else 100 if accent else 85 if sub == 0 else 60})
    return result


def tapped_bpm(timestamps: list[float]) -> float | None:
    if len(timestamps) < 2:
        return None
    gaps = [b - a for a, b in zip(timestamps, timestamps[1:])]
    if any(g <= 0 for g in gaps):
        raise ValueError("Tap timestamps must increase.")
    value = 60 / statistics.median(gaps[-8:])
    return value if 20 <= value <= 300 else None


TUNINGS = {"Guitar": "E2 A2 D3 G3 B3 E4", "Bass": "E1 A1 D2 G2",
           "Ukulele (high G)": "G4 C4 E4 A4", "Drop D guitar": "D2 A2 D3 G3 B3 E4"}


def fretboard(tuning: str, frets: int = 12, capo: int = 0) -> list[list[Note]]:
    strings = parse_notes(tuning, 12)
    if not 1 <= frets <= 24 or not 0 <= capo <= 12:
        raise ValueError("Choose 1–24 frets and capo 0–12.")
    if any(n.midi + capo + frets > 127 for n in strings):
        raise ValueError("This fretboard exceeds the MIDI range.")
    return [[Note.from_midi(n.midi + capo + f) for f in range(frets + 1)] for n in strings]


# Only text-complete exercises: no hidden staff/audio stimulus or performance input.
WORKSHEET_TYPES = ("interval_construction", "triad_spelling", "roman_numeral_build",
                   "modal_degree", "dominant_tendency", "applied_target", "nonchord_tone",
                   "chromatic_function", "modulation_evidence", "tonal_phrase")


def worksheet(types: list[str], difficulty: float, count: int, seed: int):
    from ..exercises.registry import generate
    if not types or any(t not in WORKSHEET_TYPES for t in types):
        raise ValueError("Select one or more supported written exercise types.")
    if not 0 <= difficulty <= 10 or not 1 <= count <= 50:
        raise ValueError("Use difficulty 0–10 and 1–50 questions.")
    rng = random.Random(seed)
    items = [generate(types[i % len(types)], difficulty, rng) for i in range(count)]
    if any(not item.grade(item.answer) for item in items):
        raise ValueError("A generated question failed its answer check.")
    return items


def worksheet_html(items, *, answers: bool = False, title: str = "Music Theory Master worksheet") -> str:
    lines = ["<!doctype html><html><head><meta charset='utf-8'><title>" + escape(title) + "</title>",
             "<style>body{font:16px Georgia,serif;max-width:800px;margin:40px auto;color:#111}li{margin:24px 0;break-inside:avoid}.space{height:55px}@media print{body{margin:15mm}}</style></head><body>",
             "<h1>" + escape(title) + (" — Answer key" if answers else "") + "</h1>"]
    if not answers:
        lines.append("<p>Name: ____________________ Date: ______________</p>")
    lines.append("<ol>")
    for ex in items:
        prompt = ex.prompt.replace("Click the staff or play it.", "Write the note name.")
        lines.append("<li>" + escape(prompt))
        if ex.choices:
            lines.append("<p>" + " · ".join(escape(str(c)) for c in ex.choices) + "</p>")
        if answers:
            # Explanations preserve spelling for note-entry answers stored as MIDI.
            lines.append("<p><strong>" + escape(ex.explanation or str(ex.answer)) + "</strong></p>")
        else:
            lines.append("<div class='space'></div>")
        lines.append("</li>")
    return "\n".join(lines + ["</ol></body></html>"])
