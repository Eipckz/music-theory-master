"""Written music-theory exercise generators."""

from __future__ import annotations

import random

from ..theory.pitch import Note, interval_between, transpose
from ..theory.scales import scale_notes, key_signature
from ..theory.chords import (
    TRIAD_QUALITIES, SEVENTH_QUALITIES, triad, seventh, figured_bass, roman_to_chord,
)
from .base import Exercise, InputMode
from .registry import register
from . import _util as U

_COMMON_INTERVALS = ["P1", "m2", "M2", "m3", "M3", "P4", "A4", "d5", "P5",
                     "m6", "M6", "m7", "M7", "P8"]
_QUALITY_NAMES = {
    "major": "Major", "minor": "Minor", "diminished": "Diminished", "augmented": "Augmented",
    "maj7": "Major 7th", "dom7": "Dominant 7th", "min7": "Minor 7th",
    "halfdim7": "Half-diminished 7th", "dim7": "Fully-diminished 7th", "minMaj7": "Minor-major 7th",
    "augMaj7": "Augmented-major 7th", "dom7b5": "Dominant 7th (b5)",
}


@register("note_identification", "theory", "Note Identification")
def note_identification(difficulty: float, rng: random.Random) -> Exercise:
    clef = rng.choice(["treble", "bass"]) if difficulty >= 2 else "treble"
    easy = difficulty < 4
    note = U.note_in_clef_range(rng, clef, easy=easy)
    with_octave = difficulty >= 5
    answer = note.name if with_octave else note.letter
    distractors = [Note(l, 0, note.octave).name if with_octave else l for l in "CDEFGAB"]
    return Exercise(
        skill_id="fund.note_names", domain="theory", etype="note_identification",
        prompt=f"Name this note ({clef} clef).",
        input_mode=InputMode.MULTIPLE_CHOICE, answer=answer,
        choices=U.choices_from(answer, distractors, rng, k=4),
        explanation=f"This note is {note.name}.", difficulty=difficulty,
        play={"mode": "note", "midi": note.midi},
        tags={"staff_prompt": {"clef": clef, "notes": [note]}},
    )


@register("interval_identification", "theory", "Interval Identification")
def interval_identification(difficulty: float, rng: random.Random) -> Exercise:
    clef = rng.choice(["treble", "bass"])
    base = U.note_in_clef_range(rng, clef, easy=True)
    max_num = 5 if difficulty < 3 else (8 if difficulty < 6 else 9)
    qualities = ["P", "M", "m"] if difficulty < 4 else ["P", "M", "m", "A", "d"]
    for _ in range(40):
        num = rng.randint(2, max_num)
        q = rng.choice(qualities)
        try:
            top = transpose(base, num, q)
        except KeyError:
            continue
        iv = interval_between(base, top)
        if 48 <= top.midi <= 84:
            break
    else:
        top = transpose(base, 5, "P")
        iv = interval_between(base, top)
    return Exercise(
        skill_id="fund.intervals", domain="theory", etype="interval_identification",
        prompt=f"Identify the interval between the two notes ({clef} clef).",
        input_mode=InputMode.MULTIPLE_CHOICE, answer=iv.name,
        choices=U.choices_from(iv.name, _interval_distractors(iv, rng), rng, k=4),
        explanation=f"{base.name} to {top.name} is a {iv.name}.", difficulty=difficulty,
        play={"mode": "interval", "low": base.midi, "high": top.midi,
              "harmonic": difficulty >= 5},
        tags={"staff_prompt": {"clef": clef, "notes": [base, top]}},
    )


def _interval_distractors(iv, rng: random.Random) -> list[str]:
    out = set()
    qual_sets = {True: ["P", "A", "d"], False: ["M", "m", "A", "d"]}
    perfecty = iv.quality in ("P",) or iv.number in (1, 4, 5, 8)
    for q in qual_sets[perfecty]:
        out.add(f"{q}{iv.number}")
    for dn in (iv.number - 1, iv.number + 1):
        if dn >= 1:
            out.add(f"{iv.quality}{dn}")
    out.update(_COMMON_INTERVALS)
    out.discard(iv.name)
    return list(out)


@register("interval_construction", "theory", "Interval Construction")
def interval_construction(difficulty: float, rng: random.Random) -> Exercise:
    clef = "treble"
    base = U.note_in_clef_range(rng, clef, easy=True)
    qualities = ["P", "M", "m"] if difficulty < 4 else ["P", "M", "m", "A", "d"]
    max_num = 5 if difficulty < 3 else 8
    for _ in range(40):
        num = rng.randint(2, max_num)
        q = rng.choice(qualities)
        try:
            top = transpose(base, num, q)
        except KeyError:
            continue
        iv = interval_between(base, top)
        if 48 <= top.midi <= 84:
            break
    else:
        top = transpose(base, 5, "P")
        iv = interval_between(base, top)
    return Exercise(
        skill_id="fund.intervals", domain="theory", etype="interval_construction",
        prompt=f"Build a {iv.name} above {base.name}. Click the staff or play it.",
        input_mode=InputMode.NOTE_ENTRY, answer=[top.midi],
        explanation=f"A {iv.name} above {base.name} is {top.name}.", difficulty=difficulty,
        reveal={"staff": {"clef": clef, "notes": [base, top]}},
        tags={"staff_prompt": {"clef": clef, "notes": [base]}, "match": "pc"},
    )


@register("scale_identification", "theory", "Scale Identification")
def scale_identification(difficulty: float, rng: random.Random) -> Exercise:
    if difficulty < 3:
        pool = ["major", "natural_minor"]
    elif difficulty < 6:
        pool = ["major", "natural_minor", "harmonic_minor", "melodic_minor", "dorian", "mixolydian"]
    else:
        pool = ["major", "harmonic_minor", "melodic_minor", "dorian", "phrygian", "lydian",
                "mixolydian", "locrian", "whole_tone", "octatonic_hw"]
    stype = rng.choice(pool)
    tonic = Note.parse(U.pick_key_name(rng, difficulty) + "4")
    notes = scale_notes(tonic, stype)
    midis = [n.midi for n in notes] + [tonic.midi + 12]
    answer = stype.replace("_", " ").title()
    distractors = [s.replace("_", " ").title() for s in pool]
    return Exercise(
        skill_id="scales.identify", domain="theory", etype="scale_identification",
        prompt="Identify the scale you hear.",
        input_mode=InputMode.MULTIPLE_CHOICE, answer=answer,
        choices=U.choices_from(answer, distractors, rng, k=4),
        explanation=f"This is a {tonic.name_no_octave} {answer} scale.", difficulty=difficulty,
        play={"mode": "melody", "midis": midis, "tempo": 132, "beats": 0.5},
        tags={"staff_prompt": {"clef": "treble", "notes": notes}},
    )


@register("scale_spelling", "theory", "Scale Spelling")
def scale_spelling(difficulty: float, rng: random.Random) -> Exercise:
    stype = "major" if difficulty < 2 else rng.choice(
        ["major", "natural_minor", "harmonic_minor", "melodic_minor"])
    tonic = Note.parse(U.pick_key_name(rng, difficulty) + "4")
    notes = scale_notes(tonic, stype)
    answer = [n.midi for n in notes]
    label = stype.replace("_", " ")
    return Exercise(
        skill_id="scales.spell", domain="theory", etype="scale_spelling",
        prompt=f"Spell the {tonic.name_no_octave} {label} scale ascending (one octave).",
        input_mode=InputMode.NOTE_ENTRY, answer=answer,
        explanation="Ascending: " + " ".join(n.name_no_octave for n in notes),
        difficulty=difficulty, reveal={"staff": {"clef": "treble", "notes": notes}},
        tags={"staff_prompt": {"clef": "treble", "notes": []}, "match": "pc"},
    )


@register("key_signature_identification", "theory", "Key Signatures")
def key_signature_identification(difficulty: float, rng: random.Random) -> Exercise:
    mode = U.pick_mode(rng, difficulty)
    tonic = Note.parse(U.pick_key_name(rng, difficulty) + "4")
    ks = key_signature(tonic, mode)
    answer = f"{tonic.name_no_octave} {mode}"
    # distractors: relative/parallel and neighbors on the circle of fifths
    distractors = [f"{Note.parse(k + '4').name_no_octave} {m}"
                   for k in U.MED_KEYS for m in ("major", "minor")]
    return Exercise(
        skill_id="scales.key_signatures", domain="theory", etype="key_signature_identification",
        prompt=f"Which key has this signature? ({ks['count']} {ks['kind']}"
               + ("s" if ks["count"] != 1 else "") + ")",
        input_mode=InputMode.MULTIPLE_CHOICE, answer=answer,
        choices=U.choices_from(answer, distractors, rng, k=4),
        explanation=f"{answer.title()} has {ks['count']} {ks['kind']}(s).",
        difficulty=difficulty,
        tags={"staff_prompt": {"clef": "treble", "notes": [], "key_sig": ks}},
    )


@register("triad_quality", "theory", "Triad Quality")
def triad_quality(difficulty: float, rng: random.Random) -> Exercise:
    pool = ["major", "minor"] if difficulty < 2 else TRIAD_QUALITIES
    quality = rng.choice(pool)
    root = Note.from_midi(U.random_midi(rng, 55, 67, white_only=difficulty < 4), prefer_sharps=True)
    ch = triad(root, quality)
    answer = _QUALITY_NAMES[quality]
    distractors = [_QUALITY_NAMES[q] for q in TRIAD_QUALITIES]
    return Exercise(
        skill_id="chords.triad_quality", domain="theory", etype="triad_quality",
        prompt="Identify the quality of this triad.",
        input_mode=InputMode.MULTIPLE_CHOICE, answer=answer,
        choices=U.choices_from(answer, distractors, rng, k=4),
        explanation=f"{ch.symbol} is a {answer.lower()} triad.", difficulty=difficulty,
        play={"mode": "chord", "midis": [n.midi for n in ch.voiced(4)]},
        tags={"staff_prompt": {"clef": "treble", "notes": ch.voiced(4)}},
    )


@register("seventh_quality", "theory", "Seventh-Chord Quality")
def seventh_quality(difficulty: float, rng: random.Random) -> Exercise:
    if difficulty < 4:
        pool = ["dom7", "maj7", "min7"]
    elif difficulty < 7:
        pool = SEVENTH_QUALITIES
    else:
        pool = SEVENTH_QUALITIES + ["augMaj7", "dom7b5"]
    quality = rng.choice(pool)
    root = Note.from_midi(U.random_midi(rng, 53, 65, white_only=difficulty < 5), prefer_sharps=True)
    ch = seventh(root, quality)
    answer = _QUALITY_NAMES[quality]
    distractors = [_QUALITY_NAMES[q] for q in SEVENTH_QUALITIES]
    return Exercise(
        skill_id="chords.seventh_quality", domain="theory", etype="seventh_quality",
        prompt="Identify the quality of this seventh chord.",
        input_mode=InputMode.MULTIPLE_CHOICE, answer=answer,
        choices=U.choices_from(answer, distractors, rng, k=4),
        explanation=f"{ch.symbol} is a {answer.lower()} chord.", difficulty=difficulty,
        play={"mode": "chord", "midis": [n.midi for n in ch.voiced(3)]},
        tags={"staff_prompt": {"clef": "treble", "notes": ch.voiced(4)}},
    )


@register("triad_spelling", "theory", "Triad Spelling")
def triad_spelling(difficulty: float, rng: random.Random) -> Exercise:
    quality = rng.choice(["major", "minor"] if difficulty < 2 else TRIAD_QUALITIES)
    root = Note.parse(U.pick_key_name(rng, difficulty) + "4")
    ch = triad(root, quality)
    return Exercise(
        skill_id="chords.triad_spell", domain="theory", etype="triad_spelling",
        prompt=f"Spell a {_QUALITY_NAMES[quality].lower()} triad on {root.name_no_octave}.",
        input_mode=InputMode.NOTE_ENTRY, answer=[n.midi for n in ch.members],
        explanation=" ".join(n.name_no_octave for n in ch.members), difficulty=difficulty,
        reveal={"staff": {"clef": "treble", "notes": ch.members}},
        tags={"staff_prompt": {"clef": "treble", "notes": []}, "match": "pc"},
    )


@register("chord_inversion", "theory", "Chord Inversions & Figured Bass")
def chord_inversion(difficulty: float, rng: random.Random) -> Exercise:
    is_seventh = difficulty >= 4 and rng.random() < 0.5
    if is_seventh:
        ch = seventh(Note.parse(U.pick_key_name(rng, difficulty) + "4"), rng.choice(["dom7", "maj7", "min7"]))
        inv = rng.randint(0, 3)
    else:
        ch = triad(Note.parse(U.pick_key_name(rng, difficulty) + "4"), rng.choice(["major", "minor"]))
        inv = rng.randint(0, 2)
    ch.inversion = inv
    answer = figured_bass(is_seventh, inv) or "root (5/3)"
    pool = ["root (5/3)", "6", "64", "7", "65", "43", "42"]
    return Exercise(
        skill_id="chords.inversions", domain="theory", etype="chord_inversion",
        prompt="What is the figured-bass symbol for this chord's inversion?",
        input_mode=InputMode.MULTIPLE_CHOICE, answer=answer,
        choices=U.choices_from(answer, pool, rng, k=4),
        explanation=f"Bass note {ch.bass.name_no_octave}: inversion figure '{answer}'.",
        difficulty=difficulty,
        play={"mode": "chord", "midis": [n.midi for n in ch.voiced(3)]},
        tags={"staff_prompt": {"clef": "bass", "notes": ch.voiced(3)}},
    )


@register("roman_numeral_analysis", "theory", "Roman-Numeral Analysis")
def roman_numeral_analysis(difficulty: float, rng: random.Random) -> Exercise:
    mode = U.pick_mode(rng, difficulty)
    key = U.pick_key_name(rng, difficulty)
    diatonic = (["I", "ii", "iii", "IV", "V", "vi", "vii\u00b0"] if mode == "major"
                else ["i", "ii\u00b0", "III", "iv", "V", "VI", "vii\u00b0"])
    if difficulty >= 6:
        diatonic += ["V7", "ii6", "V65"]
        # Secondary functions only in nearer keys, where enharmonic spelling
        # stays sane (avoids triple-accidental territory in remote keys).
        if key_signature(Note.parse(key + "4"), mode)["count"] <= 4:
            diatonic += ["V/V", "V/vi"]
    figure = rng.choice(diatonic)
    ch = roman_to_chord(figure.replace("\u00b0", "o"), key, mode)
    notes = ch.voiced(3)
    distractors = diatonic + ["I", "IV", "V", "vi", "ii"]
    return Exercise(
        skill_id="harmony.roman_numerals", domain="theory", etype="roman_numeral_analysis",
        prompt=f"In {key} {mode}, what is the roman numeral of this chord?",
        input_mode=InputMode.MULTIPLE_CHOICE, answer=figure,
        choices=U.choices_from(figure, distractors, rng, k=4),
        explanation=f"{ch.symbol} = {figure} in {key} {mode}.", difficulty=difficulty,
        play={"mode": "chord", "midis": [n.midi for n in notes]},
        tags={"staff_prompt": {"clef": "treble", "notes": notes}},
    )


@register("roman_numeral_build", "theory", "Build From Roman Numeral")
def roman_numeral_build(difficulty: float, rng: random.Random) -> Exercise:
    mode = U.pick_mode(rng, difficulty)
    key = U.pick_key_name(rng, difficulty)
    diatonic = (["I", "ii", "iii", "IV", "V", "vi"] if mode == "major"
                else ["i", "III", "iv", "V", "VI"])
    if difficulty >= 6:
        diatonic += ["V7", "ii7", "IV"]
    figure = rng.choice(diatonic)
    ch = roman_to_chord(figure, key, mode)
    return Exercise(
        skill_id="harmony.roman_build", domain="theory", etype="roman_numeral_build",
        prompt=f"In {key} {mode}, spell the {figure} chord (root position).",
        input_mode=InputMode.NOTE_ENTRY, answer=[n.pc for n in ch.members],
        explanation=" ".join(n.name_no_octave for n in ch.members), difficulty=difficulty,
        reveal={"staff": {"clef": "treble", "notes": ch.members}},
        tags={"staff_prompt": {"clef": "treble", "notes": [], "key_sig": key_signature(Note.parse(key + '4'), mode)},
              "match": "pc"},
    )


@register("note_placement", "theory", "Place the Note")
def note_placement(difficulty: float, rng: random.Random) -> Exercise:
    """Reverse note identification: given a name, put it on the staff."""
    clef = rng.choice(["treble", "bass"]) if difficulty >= 2 else "treble"
    easy = difficulty < 4
    # keep inside the on-screen entry piano's range (48..84)
    if clef == "bass":
        low, high = (48, 60) if easy else (48, 64)
    else:
        low, high = (60, 79) if easy else (55, 84)
    note = Note.from_midi(U.random_midi(rng, low, high, white_only=easy),
                          prefer_sharps=True)
    return Exercise(
        skill_id="fund.note_names", domain="theory", etype="note_placement",
        prompt=f"Enter the note {note.name} ({clef} clef). Watch it land on the staff.",
        input_mode=InputMode.NOTE_ENTRY, answer=[note.midi],
        explanation=f"{note.name} sits here on the {clef} staff.",
        difficulty=difficulty,
        reveal={"staff": {"clef": clef, "notes": [note]}},
        tags={"staff_prompt": {"clef": clef, "notes": []}},
    )


@register("key_signature_build", "theory", "Build Key Signatures")
def key_signature_build(difficulty: float, rng: random.Random) -> Exercise:
    """Forward direction: name a key, pick its signature."""
    mode = U.pick_mode(rng, difficulty)
    key = U.pick_key_name(rng, difficulty)
    sig = key_signature(Note.parse(key + "4"), mode)

    def describe(s: dict) -> str:
        if s["count"] == 0:
            return "No sharps or flats"
        names = ", ".join(s["letters"])
        plural = "sharp" if s["kind"] == "sharp" else "flat"
        return f"{s['count']} {plural}{'s' if s['count'] != 1 else ''} ({names})"

    answer = describe(sig)
    orders = {"sharp": "FCGDAEB", "flat": "BEADGCF"}
    distractors = []
    for dc in (sig["count"] - 1, sig["count"] + 1, sig["count"] + 2, 7 - sig["count"]):
        for kind in ("sharp", "flat"):
            if 0 <= dc <= 7:
                d = describe({"count": dc, "kind": kind, "letters": list(orders[kind][:dc])})
                if d != answer:
                    distractors.append(d)
    # same count, opposite kind, is the classic trap
    flip = "flat" if sig["kind"] == "sharp" else "sharp"
    if sig["count"]:
        distractors.insert(0, describe({"count": sig["count"], "kind": flip,
                                        "letters": list(orders[flip][:sig["count"]])}))
    return Exercise(
        skill_id="scales.key_signatures", domain="theory", etype="key_signature_build",
        prompt=f"Which key signature does {key} {mode} have?",
        input_mode=InputMode.MULTIPLE_CHOICE, answer=answer,
        choices=U.choices_from(answer, distractors, rng, k=4),
        explanation=f"{key} {mode}: {answer}.", difficulty=difficulty,
        reveal={"staff": {"clef": "treble", "key_sig": sig, "notes": []}},
    )


@register("inversion_build", "theory", "Build Chords in Inversion")
def inversion_build(difficulty: float, rng: random.Random) -> Exercise:
    """Construct a triad/seventh in a named inversion; the bass note must be
    the named chord member (octaves above it are free)."""
    root = Note.from_midi(U.random_midi(rng, 48, 59, white_only=difficulty < 5),
                          prefer_sharps=True)
    if difficulty < 6:
        quality = rng.choice(TRIAD_QUALITIES if difficulty >= 3 else ["major", "minor"])
        ch = triad(root, quality)
    else:
        quality = rng.choice(SEVENTH_QUALITIES)
        ch = seventh(root, quality)
    members = list(ch.members)
    inv = rng.randint(0, len(members) - 1) if difficulty >= 3 else rng.randint(0, 1)
    inv_names = {0: "root position", 1: "first inversion", 2: "second inversion",
                 3: "third inversion"}
    rotated = members[inv:] + members[:inv]
    # voice ascending from the bass for the canonical answer
    voiced = []
    last = None
    for n in rotated:
        m = n.midi
        while last is not None and m <= last:
            m += 12
        voiced.append(m)
        last = m

    def check(resp, ans) -> bool:
        r = [int(x) for x in (resp or [])]
        if len(r) != len(ans):
            return False
        if {x % 12 for x in r} != {x % 12 for x in ans}:
            return False
        return min(r) % 12 == ans[0] % 12   # the named member is in the bass

    name = f"{ch.symbol} in {inv_names[inv]}"
    return Exercise(
        skill_id="chords.inversions", domain="theory", etype="inversion_build",
        prompt=f"Play {name} (lowest note = the {['root', '3rd', '5th', '7th'][inv]}).",
        input_mode=InputMode.PIANO, answer=voiced, checker=check,
        explanation=f"{name}: " + " ".join(Note.from_midi(m).name for m in voiced),
        difficulty=difficulty,
        reveal={"highlight": voiced},
        play={"mode": "chord", "midis": voiced},
    )
