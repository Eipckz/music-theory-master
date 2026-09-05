"""Pre-graduate bridge generators.

These exercises connect advanced tonal study to graduate analytical work in
three coordinated domains: pitch-class/set reasoning, post-tonal hearing, and
keyboard realization.  They intentionally teach the representation before
asking for normal/prime forms or complete twelve-tone matrices.
"""

from __future__ import annotations

import random

from ..theory.neoriemann import nr_transform, parse_triad, triad_name, triad_pcs
from ..theory.settheory import interval_class, pc_label, pc_name
from . import _util as U
from .base import Exercise, InputMode
from .registry import register


def _pc_midi(pc: int, octave_floor: int = 60) -> int:
    return octave_floor + (int(pc) % 12)


def _collection_midis(pcs: list[int]) -> list[int]:
    """Place an unordered pc set in a compact, audible middle-register voicing."""
    ordered = sorted({int(pc) % 12 for pc in pcs})
    return [_pc_midi(pc) for pc in ordered]


@register("pitch_class_conversion", "theory", "Pitch Classes: Notes ↔ Numbers")
def pitch_class_conversion(difficulty: float, rng: random.Random) -> Exercise:
    pc = rng.randrange(12)
    prefer_flats = difficulty >= 3 and rng.random() < 0.5
    note = pc_name(pc, prefer_flats=prefer_flats)
    answer = str(pc)
    choices = U.choices_from(answer, [str(x) for x in range(12) if x != pc], rng, k=4)
    return Exercise(
        skill_id="posttonal.pitch_classes", domain="theory",
        etype="pitch_class_conversion",
        prompt=f"Using C=0, what pitch-class number is {note}?",
        input_mode=InputMode.MULTIPLE_CHOICE, answer=answer, choices=choices,
        explanation=f"{note} is pitch class {pc}. Octave does not change the number.",
        teach="Pitch classes use a fixed chromatic clock: C=0, C#/Db=1, ... B=11.",
        hint="Count chromatic half steps upward from C=0.",
        difficulty=difficulty,
    )


@register("pitch_class_clock", "theory", "Pitch-Class Clock")
def pitch_class_clock(difficulty: float, rng: random.Random) -> Exercise:
    start = rng.randrange(12)
    n = rng.randint(1, 6 if difficulty < 4 else 11)
    result = (start + n) % 12
    answer = str(result)
    choices = U.choices_from(answer, [str(x) for x in range(12) if x != result], rng, k=4)
    return Exercise(
        skill_id="posttonal.pitch_classes", domain="theory", etype="pitch_class_clock",
        prompt=f"Rotate pitch class {start} clockwise by {n} semitone position(s). Where do you land?",
        input_mode=InputMode.MULTIPLE_CHOICE, answer=answer, choices=choices,
        explanation=f"({start} + {n}) mod 12 = {result} ({pc_name(result)}).",
        teach="A pitch-class clock has 12 positions; arithmetic wraps around modulo 12.",
        hint="Add, then subtract 12 if the total reaches 12 or more.",
        difficulty=difficulty,
    )


@register("interval_class_identification", "theory", "Interval Classes 1–6")
def interval_class_identification(difficulty: float, rng: random.Random) -> Exercise:
    a, b = rng.sample(range(12), 2)
    answer = str(interval_class(a, b))
    choices = U.choices_from(answer, [str(x) for x in range(1, 7) if str(x) != answer], rng, k=4)
    return Exercise(
        skill_id="posttonal.interval_classes", domain="theory",
        etype="interval_class_identification",
        prompt=f"What interval class is formed by pitch classes {a} and {b}?",
        input_mode=InputMode.MULTIPLE_CHOICE, answer=answer, choices=choices,
        explanation=f"The distances are {(b-a)%12} and {(a-b)%12}; the shorter is IC {answer}.",
        teach="Interval class chooses the shorter direction around the 12-position clock, so only 1–6 occur.",
        hint="Find both directed distances; keep the smaller one.",
        difficulty=difficulty,
        play={"mode": "interval", "low": 60, "high": 60 + interval_class(a, b),
              "harmonic": difficulty >= 4},
    )


@register("posttonal_interval_ear", "aural", "Hear an Interval Class")
def posttonal_interval_ear(difficulty: float, rng: random.Random) -> Exercise:
    ic = rng.randint(1, 6)
    directed = ic if ic == 6 or rng.random() < 0.5 else 12 - ic
    answer = str(ic)
    choices = U.choices_from(answer, [str(x) for x in range(1, 7) if x != ic], rng, k=4)
    return Exercise(
        skill_id="aural.posttonal_intervals", domain="aural", etype="posttonal_interval_ear",
        prompt="Listen, then identify the INTERVAL CLASS (1–6), not the tonal interval name.",
        input_mode=InputMode.MULTIPLE_CHOICE, answer=answer, choices=choices,
        explanation=f"The span is {directed} semitones; its shortest clock distance is IC {ic}.",
        teach="An interval and its inversion share an interval class: m2/M7 are IC1, P4/P5 are IC5.",
        hint="If the span sounds larger than a tritone, invert it mentally.",
        difficulty=difficulty,
        play={"mode": "interval", "low": 60, "high": 60 + directed,
              "harmonic": difficulty >= 5},
        tags={"replayable": True},
    )


@register("pcset_cardinality_ear", "aural", "Hear Pitch-Set Cardinality")
def pcset_cardinality_ear(difficulty: float, rng: random.Random) -> Exercise:
    cardinality = rng.randint(3, 4 if difficulty < 5 else 6)
    pcs = sorted(rng.sample(range(12), cardinality))
    midis = _collection_midis(pcs)
    answer = str(cardinality)
    choices = U.choices_from(answer, [str(x) for x in range(2, 8) if x != cardinality], rng, k=4)
    return Exercise(
        skill_id="aural.pc_collections", domain="aural", etype="pcset_cardinality_ear",
        prompt="How many distinct pitch classes are in this collection?",
        input_mode=InputMode.MULTIPLE_CHOICE, answer=answer, choices=choices,
        explanation=f"The collection has {cardinality} pitch classes: "
                    + " ".join(pc_label(pc) for pc in pcs) + ".",
        teach="Cardinality counts distinct pitch classes, not register doublings or tonal chord members.",
        hint="Listen to the arpeggiation once for separate attacks, then the chord for the total color.",
        difficulty=difficulty,
        play={"mode": "chord", "midis": midis, "arpeggiate": True, "tempo": 84},
        tags={"replayable": True},
    )


@register("plr_transformation_ear", "aural", "Hear P/L/R Voice Leading")
def plr_transformation_ear(difficulty: float, rng: random.Random) -> Exercise:
    root = rng.randrange(12)
    source = (root, rng.random() < 0.5)
    op = rng.choice("PLR")
    target = nr_transform(source, op)
    choices = ["P", "L", "R"]
    return Exercise(
        skill_id="aural.neo_riemannian", domain="aural", etype="plr_transformation_ear",
        prompt=f"The first chord is {triad_name(source)}. Which one-note transformation leads to the second chord?",
        input_mode=InputMode.MULTIPLE_CHOICE, answer=op, choices=choices,
        explanation=f"{triad_name(source)} --{op}--> {triad_name(target)}; two pitch classes remain common.",
        teach="P changes the third, R exchanges relative major/minor, and L performs leading-tone exchange.",
        hint="Track the one pitch that moves while two common tones stay fixed.",
        difficulty=difficulty,
        play={"mode": "harmonic",
              "chords": [_collection_midis(triad_pcs(source)), _collection_midis(triad_pcs(target))],
              "tempo": 68, "beats": 2.0},
        tags={"replayable": True},
    )


@register("play_pitch_class_set", "piano", "Play a Pitch-Class Set")
def play_pitch_class_set(difficulty: float, rng: random.Random) -> Exercise:
    cardinality = 3 if difficulty < 4 else rng.randint(3, 5)
    pcs = sorted(rng.sample(range(12), cardinality))
    reveal = _collection_midis(pcs)
    return Exercise(
        skill_id="piano.pc_collections", domain="piano", etype="play_pitch_class_set",
        prompt="Play one instance of each pitch class in {" + " ".join(pc_label(pc) for pc in pcs) + "}.",
        input_mode=InputMode.PIANO, answer=pcs,
        explanation="Any octave is valid; the required pitch classes are "
                    + ", ".join(f"{pc_label(pc)}={pc_name(pc)}" for pc in pcs) + ".",
        teach="Pitch-class sets ignore octave, so keyboard position may change while membership stays the same.",
        hint="Convert each number from C=0, then choose a comfortable compact voicing.",
        difficulty=difficulty, reveal={"highlight": reveal},
        tags={"match": "pc", "expect_count": cardinality},
    )


@register("play_row_segment", "piano", "Play a Row Segment")
def play_row_segment(difficulty: float, rng: random.Random) -> Exercise:
    length = 4 if difficulty < 5 else rng.randint(5, 8)
    pcs = rng.sample(range(12), length)
    midis = [_pc_midi(pc) for pc in pcs]
    return Exercise(
        skill_id="piano.row_realization", domain="piano", etype="play_row_segment",
        prompt="Play this ordered row segment: [" + " ".join(pc_label(pc) for pc in pcs) + "].",
        input_mode=InputMode.NOTE_ENTRY, answer=pcs,
        explanation="Order matters; octave does not. Notes: "
                    + " – ".join(pc_name(pc) for pc in pcs) + ".",
        teach="A twelve-tone row controls pitch-class order; register, rhythm, articulation, and voicing remain compositional choices.",
        hint="Translate one pitch class at a time and keep the displayed order.",
        difficulty=difficulty, reveal={"highlight": midis},
        tags={"match": "pc", "expect_count": length},
    )


@register("play_plr_transform", "piano", "Play a P/L/R Transformation")
def play_plr_transform(difficulty: float, rng: random.Random) -> Exercise:
    roots = ["C", "D", "E", "F", "G", "A", "Bb"]
    name = rng.choice(roots) + rng.choice(["", "m"])
    source = parse_triad(name)
    op = rng.choice("PLR")
    target = nr_transform(source, op)
    pcs = triad_pcs(target)
    return Exercise(
        skill_id="piano.neo_riemannian", domain="piano", etype="play_plr_transform",
        prompt=f"Starting from {name}, play the triad produced by {op}.",
        input_mode=InputMode.PIANO, answer=pcs,
        explanation=f"{name} --{op}--> {triad_name(target)}. Keep two common tones and move one voice.",
        teach="Neo-Riemannian P, L, and R connect major/minor triads through parsimonious voice leading.",
        hint="Hold the two common tones; identify the single note the chosen transformation changes.",
        difficulty=difficulty, reveal={"highlight": _collection_midis(pcs)},
        tags={"match": "pc", "expect_count": 3},
    )
