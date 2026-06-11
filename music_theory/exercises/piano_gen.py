"""Keyboard-skills exercise generators. Answers are played on the on-screen
piano or a connected MIDI keyboard (InputMode.PIANO collects pressed notes)."""

from __future__ import annotations

import random

from ..theory.pitch import Note, transpose
from ..theory.scales import scale_notes
from ..theory.chords import triad, TRIAD_QUALITIES
from .base import Exercise, InputMode
from .registry import register
from . import _util as U


@register("play_note", "piano", "Play a Note")
def play_note(difficulty: float, rng: random.Random) -> Exercise:
    midi = U.random_midi(rng, 60, 72, white_only=difficulty < 3)
    note = Note.from_midi(midi)
    return Exercise(
        skill_id="piano.find_notes", domain="piano", etype="play_note",
        prompt=f"Play {note.name} on the keyboard.",
        input_mode=InputMode.PIANO, answer=[midi],
        explanation=f"{note.name} is MIDI {midi}.", difficulty=difficulty,
        reveal={"highlight": [midi]},
        tags={"match": "exact", "expect_count": 1},
    )


@register("play_interval", "piano", "Play an Interval")
def play_interval(difficulty: float, rng: random.Random) -> Exercise:
    base = Note.from_midi(U.random_midi(rng, 58, 67, white_only=True))
    quals = ["P", "M", "m"] if difficulty < 4 else ["P", "M", "m", "A", "d"]
    for _ in range(30):
        num = rng.randint(2, 5 if difficulty < 3 else 8)
        q = rng.choice(quals)
        try:
            top = transpose(base, num, q)
            break
        except KeyError:
            continue
    else:
        top = transpose(base, 5, "P")
    from ..theory.pitch import interval_between
    iv = interval_between(base, top)
    return Exercise(
        skill_id="piano.intervals", domain="piano", etype="play_interval",
        prompt=f"Play a {iv.name} above {base.name}.",
        input_mode=InputMode.PIANO, answer=[base.midi, top.midi],
        explanation=f"{base.name} + {iv.name} = {top.name}.", difficulty=difficulty,
        reveal={"highlight": [base.midi, top.midi]},
        tags={"match": "exact", "expect_count": 2},
    )


@register("play_triad", "piano", "Play a Triad")
def play_triad(difficulty: float, rng: random.Random) -> Exercise:
    quality = rng.choice(["major", "minor"] if difficulty < 2 else TRIAD_QUALITIES)
    root = Note.from_midi(U.random_midi(rng, 60, 67, white_only=difficulty < 4))
    ch = triad(root, quality)
    from .theory_gen import _QUALITY_NAMES
    return Exercise(
        skill_id="piano.chords", domain="piano", etype="play_triad",
        prompt=f"Play a {_QUALITY_NAMES[quality].lower()} triad on {root.name_no_octave}.",
        input_mode=InputMode.PIANO, answer=[n.pc for n in ch.members],
        explanation=" ".join(n.name_no_octave for n in ch.members), difficulty=difficulty,
        reveal={"highlight": [n.midi for n in ch.voiced(4)]},
        tags={"match": "pc", "expect_count": 3},
    )


@register("play_scale", "piano", "Play a Scale")
def play_scale(difficulty: float, rng: random.Random) -> Exercise:
    stype = "major" if difficulty < 2 else rng.choice(["major", "natural_minor", "harmonic_minor"])
    tonic = Note.from_midi(U.random_midi(rng, 60, 67, white_only=difficulty < 3))
    notes = scale_notes(tonic, stype)
    seq = [n.midi for n in notes] + [tonic.midi + 12]
    label = stype.replace("_", " ")
    return Exercise(
        skill_id="piano.scales", domain="piano", etype="play_scale",
        prompt=f"Play the {tonic.name_no_octave} {label} scale ascending (one octave).",
        input_mode=InputMode.NOTE_ENTRY, answer=seq,
        explanation=" ".join(n.name_no_octave for n in notes), difficulty=difficulty,
        reveal={"highlight": seq},
        tags={"match": "pc", "expect_count": len(seq)},
    )
