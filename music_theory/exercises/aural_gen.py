"""Aural-skills exercise generators, including melodic dictation (a first-class
exercise available from the very first lesson)."""

from __future__ import annotations

import random

from ..theory.pitch import Note
from ..theory.scales import SCALE_TYPES, scale_notes, key_signature
from ..theory.chords import triad, seventh, roman_to_chord
from .base import Exercise, InputMode
from .registry import register
from . import _util as U

_INTERVALS_BY_DIFF = {
    0: [("P5", 7), ("P8", 12), ("M3", 4)],
    1: [("P5", 7), ("P4", 5), ("M3", 4), ("m3", 3), ("P8", 12)],
    2: [("M2", 2), ("m2", 1), ("M3", 4), ("m3", 3), ("P4", 5), ("P5", 7), ("M6", 9), ("m6", 8)],
    3: [("M2", 2), ("m2", 1), ("M3", 4), ("m3", 3), ("P4", 5), ("A4", 6), ("P5", 7),
        ("m6", 8), ("M6", 9), ("m7", 10), ("M7", 11), ("P8", 12)],
}


def _scale_collection(tonic: Note, mode: str, low: int, high: int) -> list[int]:
    stype = "major" if mode == "major" else "harmonic_minor"
    pcs = {(tonic.pc + off) % 12 for off in SCALE_TYPES[stype]}
    return [m for m in range(low, high + 1) if m % 12 in pcs]


def _generate_melody(rng: random.Random, tonic: Note, mode: str, length: int,
                     leaps: bool) -> list[int]:
    coll = _scale_collection(tonic, mode, 60, 79)
    if not coll:
        coll = list(range(60, 80))
    tonic_idxs = [i for i, m in enumerate(coll) if m % 12 == tonic.pc]
    start = min(tonic_idxs, key=lambda i: abs(coll[i] - 67)) if tonic_idxs else len(coll) // 2
    steps = [-2, -1, -1, 1, 1, 2]
    if leaps:
        steps += [-4, -3, 3, 4]
    idx = start
    out = [coll[idx]]
    for _ in range(length - 2):
        idx = max(0, min(len(coll) - 1, idx + rng.choice(steps)))
        out.append(coll[idx])
    # resolve to a tonic for closure
    if tonic_idxs:
        idx = min(tonic_idxs, key=lambda i: abs(i - idx))
    out.append(coll[idx])
    return out


@register("interval_recognition", "aural", "Interval Recognition (Ear)")
def interval_recognition(difficulty: float, rng: random.Random) -> Exercise:
    pool = _INTERVALS_BY_DIFF[min(3, U.band(difficulty))]
    name, semis = rng.choice(pool)
    low = U.random_midi(rng, 57, 69)
    harmonic = difficulty >= 5 and rng.random() < 0.5
    descending = difficulty >= 4 and rng.random() < 0.35
    high = low + semis
    if descending:
        low, high = high, low
    answer = name
    distractors = [n for n, _ in _INTERVALS_BY_DIFF[3]]
    return Exercise(
        skill_id="aural.intervals", domain="aural", etype="interval_recognition",
        prompt="Which interval do you hear?" + (" (harmonic)" if harmonic else ""),
        input_mode=InputMode.MULTIPLE_CHOICE, answer=answer,
        choices=U.choices_from(answer, distractors, rng, k=4),
        explanation=f"That was a {name}.", difficulty=difficulty,
        play={"mode": "interval", "low": min(low, high), "high": max(low, high),
              "harmonic": harmonic} if harmonic else
             {"mode": "melody", "midis": [low, high], "tempo": 90, "beats": 1.0},
        tags={"replayable": True},
    )


@register("chord_quality_ear", "aural", "Chord Quality (Ear)")
def chord_quality_ear(difficulty: float, rng: random.Random) -> Exercise:
    if difficulty < 2:
        pool = ["major", "minor"]
    elif difficulty < 4:
        pool = ["major", "minor", "diminished", "augmented"]
    elif difficulty < 7:
        pool = ["major", "minor", "diminished", "augmented", "dom7", "maj7", "min7", "halfdim7", "dim7"]
    else:
        # the full modern palette - the colors contemporary ears live on
        pool = ["major", "minor", "diminished", "augmented", "dom7", "maj7", "min7",
                "halfdim7", "dim7", "minMaj7", "augMaj7", "dom7b5"]
    quality = rng.choice(pool)
    root = U.random_midi(rng, 55, 64)
    builder = triad if quality in ("major", "minor", "diminished", "augmented") else seventh
    ch = builder(Note.from_midi(root), quality)
    from .theory_gen import _QUALITY_NAMES
    answer = _QUALITY_NAMES[quality]
    distractors = [_QUALITY_NAMES[q] for q in pool]
    return Exercise(
        skill_id="aural.chord_quality", domain="aural", etype="chord_quality_ear",
        prompt="What is the quality of the chord you hear?",
        input_mode=InputMode.MULTIPLE_CHOICE, answer=answer,
        choices=U.choices_from(answer, distractors, rng, k=4),
        explanation=f"That was a {answer.lower()} chord.", difficulty=difficulty,
        play={"mode": "chord", "midis": [n.midi for n in ch.voiced(4)],
              "arpeggiate": difficulty < 2}, tags={"replayable": True},
    )


@register("scale_mode_ear", "aural", "Scale / Mode (Ear)")
def scale_mode_ear(difficulty: float, rng: random.Random) -> Exercise:
    if difficulty < 3:
        pool = ["major", "natural_minor"]
    elif difficulty < 6:
        pool = ["major", "natural_minor", "harmonic_minor", "dorian", "mixolydian"]
    else:
        pool = ["major", "harmonic_minor", "melodic_minor", "dorian", "phrygian",
                "lydian", "mixolydian", "locrian", "whole_tone"]
    stype = rng.choice(pool)
    tonic = Note.from_midi(U.random_midi(rng, 60, 67))
    notes = scale_notes(tonic, stype)
    midis = [n.midi for n in notes] + [tonic.midi + 12]
    answer = stype.replace("_", " ").title()
    distractors = [s.replace("_", " ").title() for s in pool]
    return Exercise(
        skill_id="aural.scales", domain="aural", etype="scale_mode_ear",
        prompt="Which scale or mode do you hear?",
        input_mode=InputMode.MULTIPLE_CHOICE, answer=answer,
        choices=U.choices_from(answer, distractors, rng, k=4),
        explanation=f"That was a {answer} scale.", difficulty=difficulty,
        play={"mode": "melody", "midis": midis, "tempo": 144, "beats": 0.5},
        tags={"replayable": True},
    )


@register("melodic_dictation", "aural", "Melodic Dictation")
def melodic_dictation(difficulty: float, rng: random.Random) -> Exercise:
    mode = "major" if difficulty < 2 else rng.choice(["major", "minor"])
    key = U.pick_key_name(rng, difficulty)
    tonic = Note.parse(key + "4")
    length = 3 if difficulty < 1 else min(9, 3 + int(difficulty))
    leaps = difficulty >= 3
    midis = _generate_melody(rng, tonic, mode, length, leaps)
    notes = [Note.from_midi(m, prefer_sharps=key not in U.HARD_KEYS or "b" not in key) for m in midis]
    tempo = 88 if difficulty < 4 else 104
    return Exercise(
        skill_id="aural.melodic_dictation", domain="aural", etype="melodic_dictation",
        prompt=f"Melodic dictation in {key} {mode}. The first note is given. "
               f"Notate the {length}-note melody (replay as needed).",
        input_mode=InputMode.NOTE_ENTRY, answer=midis,
        explanation="Melody: " + " ".join(n.name_no_octave for n in notes),
        difficulty=difficulty,
        play={"mode": "melody", "midis": midis, "tempo": tempo, "beats": 1.0},
        reveal={"staff": {"clef": "treble", "notes": notes,
                          "key_sig": key_signature(tonic, mode)}},
        tags={"replayable": True, "match": "exact", "given_first": midis[0],
              "key_sig": key_signature(tonic, mode),
              "staff_prompt": {"clef": "treble", "notes": [], "key_sig": key_signature(tonic, mode)}},
    )


# -- multi-part dictation ----------------------------------------------------
_VOICE_RANGES = {           # comfortable SATB-ish ranges (midi)
    "Soprano": (60, 79),
    "Alto": (55, 72),
    "Tenor": (48, 65),
    "Bass": (40, 57),
}
_VOICE_SETS = {2: ["Soprano", "Bass"], 3: ["Soprano", "Alto", "Bass"],
               4: ["Soprano", "Alto", "Tenor", "Bass"]}


def _nearest_chord_tone(prev: int, pcs: list[int], lo: int, hi: int,
                        below: int | None, above: int | None) -> int:
    """The chord tone closest to ``prev`` that stays in range and keeps voice
    order (strictly between the neighbouring voices when given)."""
    best, best_cost = None, None
    for pc in pcs:
        for octave in range(lo // 12, hi // 12 + 2):
            cand = octave * 12 + pc
            if not (lo <= cand <= hi):
                continue
            if below is not None and cand <= below:
                continue
            if above is not None and cand >= above:
                continue
            cost = abs(cand - prev)
            if best_cost is None or cost < best_cost:
                best, best_cost = cand, cost
    return best if best is not None else max(lo, min(hi, prev))


def _voice_progression(rng: random.Random, key: str, mode: str,
                       prog: list[str], n_voices: int) -> list[list[int]]:
    """Voice a progression into ``n_voices`` independent lines (top first)."""
    names = _VOICE_SETS[n_voices]
    chords_pcs: list[list[int]] = []
    bass_pcs: list[int] = []
    for fig in prog:
        try:
            ch = roman_to_chord(fig.replace("°", "o"), key, mode)
        except Exception:  # noqa: BLE001 - same resilience as harmonic dictation
            ch = roman_to_chord("I", key, mode)
        chords_pcs.append([n.pc for n in ch.members])
        bass_pcs.append(ch.bass.pc)
    voices: list[list[int]] = [[] for _ in names]
    for step, pcs in enumerate(chords_pcs):
        prev_col = [v[step - 1] if step else None for v in voices]
        col: list[int | None] = [None] * len(names)
        # bass first (lowest voice anchors the chord) ...
        b = len(names) - 1
        lo, hi = _VOICE_RANGES[names[b]]
        target = prev_col[b] if prev_col[b] is not None else (lo + hi) // 2
        col[b] = _nearest_chord_tone(target, [bass_pcs[step]], lo, hi, None, None)
        # ... then upper voices top-down, keeping strict ordering
        for vi in range(b - 1, -1, -1):
            lo, hi = _VOICE_RANGES[names[vi]]
            start = prev_col[vi] if prev_col[vi] is not None else hi - 5
            below = col[vi + 1]
            col[vi] = _nearest_chord_tone(start, pcs, lo, hi, below, None)
        for vi in range(len(names)):
            voices[vi].append(int(col[vi]))
    return voices


@register("multipart_dictation", "aural", "Multi-Part Dictation")
def multipart_dictation(difficulty: float, rng: random.Random) -> Exercise:
    """Two to four simultaneous voices; transcribe every line. The bridge from
    single-line dictation to full-texture hearing (outer voices first!)."""
    n_voices = 2 if difficulty < 5 else 3 if difficulty < 7.5 else 4
    mode = "major" if difficulty < 5 else rng.choice(["major", "minor"])
    key = U.pick_key_name(rng, difficulty)
    if difficulty < 4:
        progs = [["I", "V", "I"], ["I", "IV", "I"], ["I", "IV", "V"]]
    elif difficulty < 6.5:
        progs = [["I", "IV", "V", "I"], ["I", "vi", "IV", "V"], ["I", "ii6", "V", "I"]]
    else:
        progs = [["I", "vi", "ii", "V", "I"], ["I", "IV", "V6", "vi"],
                 ["i", "iv", "V", "i"], ["I", "V/V", "V", "I"]]
    prog = rng.choice(progs)
    if mode == "minor":
        prog = [p.lower() if p in ("I", "IV") else p for p in prog]
    names = _VOICE_SETS[n_voices]
    voices = _voice_progression(rng, key, mode, prog, n_voices)
    chords = [[v[i] for v in voices] for i in range(len(prog))]
    lines = "<br>".join(
        f"{nm}: " + " ".join(Note.from_midi(m).name for m in v)
        for nm, v in zip(names, voices))
    tonic = Note.parse(key + "4")
    return Exercise(
        skill_id="aural.multipart", domain="aural", etype="multipart_dictation",
        prompt=f"Multi-part dictation in {key} {mode}: {len(prog)} chords, "
               f"{n_voices} voices ({', '.join(names)}). The first chord is given. "
               "Notate every voice - outer voices first, then fill the middle.",
        input_mode=InputMode.MULTI_VOICE, answer=voices,
        explanation=f"The voices were:<br>{lines}",
        difficulty=difficulty,
        play={"mode": "harmonic", "chords": chords, "tempo": 66, "beats": 2.0},
        tags={"replayable": True, "match": "exact",
              "voice_names": names,
              "given_first_each": [v[0] for v in voices],
              "key_sig": key_signature(tonic, mode)},
    )


_RHYTHM_CELLS = {
    0: [[1.0], [0.5, 0.5], [2.0]],
    1: [[1.0], [0.5, 0.5], [1.5, 0.5], [0.5, 0.5, 1.0]],
    2: [[1.0], [0.5, 0.5], [0.25, 0.25, 0.5], [1.5, 0.5], [0.75, 0.25]],
}


@register("rhythmic_dictation", "aural", "Rhythmic Dictation")
def rhythmic_dictation(difficulty: float, rng: random.Random) -> Exercise:
    cells = _RHYTHM_CELLS[min(2, U.band(difficulty))]
    beats = 4
    pattern: list[float] = []
    total = 0.0
    while total < beats - 0.001:
        cell = rng.choice(cells)
        if total + sum(cell) <= beats + 0.001:
            pattern.extend(cell)
            total += sum(cell)
        else:
            pattern.append(beats - total)
            total = beats
    pitch = 67
    items = [(pitch, d) for d in pattern]
    return Exercise(
        skill_id="aural.rhythmic_dictation", domain="aural", etype="rhythmic_dictation",
        prompt="Reproduce the rhythm you hear (4 beats).",
        input_mode=InputMode.RHYTHM, answer=pattern,
        explanation="Durations (beats): " + ", ".join(str(d) for d in pattern),
        difficulty=difficulty,
        play={"mode": "sequence", "items": items, "tempo": 96},
        tags={"replayable": True, "beats": beats},
    )


@register("harmonic_dictation", "aural", "Harmonic Dictation")
def harmonic_dictation(difficulty: float, rng: random.Random) -> Exercise:
    mode = "major" if difficulty < 4 else rng.choice(["major", "minor"])
    key = U.pick_key_name(rng, difficulty)
    if difficulty < 3:
        progs = [["I", "IV", "V", "I"], ["I", "V", "I"], ["I", "vi", "IV", "V"]]
    elif difficulty < 6:
        progs = [["I", "IV", "V", "I"], ["I", "vi", "ii", "V"], ["I", "IV", "I", "V"],
                 ["I", "ii6", "V", "I"]]
    else:
        progs = [["I", "V6", "vi", "IV"], ["I", "V/V", "V", "I"], ["i", "iv", "V", "i"],
                 ["I", "vi", "IV", "V7"]]
    prog = rng.choice(progs)
    if mode == "minor":
        prog = [p.lower() if p in ("I", "IV", "vi") else p for p in prog]
    chords = []
    for fig in prog:
        try:
            ch = roman_to_chord(fig.replace("\u00b0", "o"), key, mode)
            chords.append([n.midi for n in ch.voiced(3)])
        except Exception:  # noqa: BLE001
            ch = roman_to_chord("I", key, mode)
            chords.append([n.midi for n in ch.voiced(3)])
    return Exercise(
        skill_id="aural.harmonic_dictation", domain="aural", etype="harmonic_dictation",
        prompt=f"Harmonic dictation in {key} {mode}: identify the progression (in order).",
        input_mode=InputMode.SEQUENCE, answer=prog,
        choices=sorted(set(prog) | {"I", "ii", "IV", "V", "vi", "V7", "V6", "ii6"}),
        explanation="Progression: " + " - ".join(prog), difficulty=difficulty,
        play={"mode": "harmonic", "chords": chords, "tempo": 80, "beats": 2.0},
        tags={"replayable": True, "match": "label"},
    )


@register("cadence_ear", "aural", "Cadence Identification (Ear)")
def cadence_ear(difficulty: float, rng: random.Random) -> Exercise:
    cadences = {
        "Authentic (PAC/IAC)": ["IV", "V", "I"],
        "Half": ["I", "IV", "V"],
        "Plagal": ["I", "IV", "I"],
        "Deceptive": ["I", "V", "vi"],
    }
    if difficulty < 2:
        cadences = {k: cadences[k] for k in ("Authentic (PAC/IAC)", "Half")}
    name = rng.choice(list(cadences))
    key = U.pick_key_name(rng, difficulty)
    chords = []
    for fig in cadences[name]:
        ch = roman_to_chord(fig, key, "major")
        chords.append([n.midi for n in ch.voiced(3)])
    return Exercise(
        skill_id="aural.cadences", domain="aural", etype="cadence_ear",
        prompt="What type of cadence do you hear?",
        input_mode=InputMode.MULTIPLE_CHOICE, answer=name,
        choices=U.choices_from(name, list(cadences), rng, k=4),
        explanation=f"That was a {name} cadence.", difficulty=difficulty,
        play={"mode": "harmonic", "chords": chords, "tempo": 76, "beats": 2.0},
        tags={"replayable": True},
    )


@register("error_detection", "aural", "Error Detection")
def error_detection(difficulty: float, rng: random.Random) -> Exercise:
    mode = "major"
    key = U.pick_key_name(rng, difficulty)
    tonic = Note.parse(key + "4")
    length = min(8, 4 + int(difficulty))
    midis = _generate_melody(rng, tonic, mode, length, leaps=difficulty >= 4)
    printed = [Note.from_midi(m) for m in midis]
    # alter one note by a step to create the "wrong" played version
    wrong_index = rng.randint(1, length - 1)
    played = list(midis)
    played[wrong_index] += rng.choice([-2, -1, 1, 2])
    answer = f"Note {wrong_index + 1}"
    choices = [f"Note {i + 1}" for i in range(length)]
    return Exercise(
        skill_id="aural.error_detection", domain="aural", etype="error_detection",
        prompt="The score is shown. One played note differs from the score. Which note?",
        input_mode=InputMode.MULTIPLE_CHOICE, answer=answer,
        choices=U.choices_from(answer, choices, rng, k=min(4, length)),
        explanation=f"Note {wrong_index + 1} was played differently.", difficulty=difficulty,
        play={"mode": "melody", "midis": played, "tempo": 100, "beats": 1.0},
        tags={"replayable": True, "staff_prompt": {"clef": "treble", "notes": printed}},
    )


@register("progression_ear", "aural", "Progression Recognition (Ear)")
def progression_ear(difficulty: float, rng: random.Random) -> Exercise:
    """The on-ramp to harmonic dictation: hear a short progression, pick its
    label from a list (no chord-by-chord entry yet)."""
    if difficulty < 3:
        pool = [["I", "IV", "V", "I"], ["I", "V", "I"], ["I", "IV", "I"]]
    elif difficulty < 6:
        pool = [["I", "IV", "V", "I"], ["I", "V", "vi", "IV"], ["I", "vi", "IV", "V"],
                ["ii", "V", "I"]]
    else:
        pool = [["I", "vi", "ii", "V"], ["I", "V", "vi", "IV"], ["ii", "V", "I"],
                ["I", "IV", "vi", "V"], ["I", "iii", "IV", "V"]]
    prog = rng.choice(pool)
    key = U.pick_key_name(rng, difficulty)
    chords = []
    for fig in prog:
        try:
            ch = roman_to_chord(fig, key, "major")
            chords.append([n.midi for n in ch.voiced(3)])
        except Exception:  # noqa: BLE001 - generators must never raise
            chords.append([48, 52, 55])
    label = " - ".join(prog)
    distractors = [" - ".join(p) for p in pool if p != prog]
    distractors += ["I - V - I", "I - IV - V - I", "ii - V - I", "I - V - vi - IV"]
    return Exercise(
        skill_id="aural.harmonic_dictation", domain="aural", etype="progression_ear",
        prompt="Which progression do you hear?",
        input_mode=InputMode.MULTIPLE_CHOICE, answer=label,
        choices=U.choices_from(label, distractors, rng, k=4),
        explanation=f"That was {label} in {key} major.", difficulty=difficulty,
        play={"mode": "harmonic", "chords": chords, "tempo": 80, "beats": 2.0},
        tags={"replayable": True},
    )
