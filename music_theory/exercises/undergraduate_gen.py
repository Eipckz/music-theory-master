"""Musicianship III–IV: tonal reasoning before post-tonal abstraction."""
from __future__ import annotations

import random

from ..theory.chords import roman_to_chord
from ..theory.pitch import Note, transpose
from ..theory.scales import scale_notes
from . import _util as U
from .base import Exercise, InputMode
from .registry import register

KEYS = ("C", "G", "D", "A", "F", "Bb", "Eb")


def _question(etype, skill, prompt, answer, alternatives, explanation, difficulty, rng, play=None):
    return Exercise(skill_id=skill, domain="theory", etype=etype, prompt=prompt,
                    input_mode=InputMode.MULTIPLE_CHOICE, answer=answer,
                    choices=U.choices_from(answer, alternatives, rng, k=4),
                    explanation=explanation, teach=explanation, difficulty=difficulty, play=play)


@register("modal_degree", "theory", "Modes: characteristic scale degrees")
def modal_degree(difficulty: float, rng: random.Random) -> Exercise:
    mode, degree, characteristic = rng.choice([
        ("dorian", 6, "natural 6 with minor 3"),
        ("phrygian", 2, "flat 2"), ("lydian", 4, "sharp 4"),
        ("mixolydian", 7, "flat 7 with major 3"),
        ("aeolian", 6, "flat 6 and flat 7"), ("locrian", 5, "flat 5 and flat 2")])
    key = rng.choice(KEYS if difficulty >= 4 else KEYS[:2])
    notes = scale_notes(Note.parse(key + "4"), mode)
    answer = notes[degree - 1].name_no_octave
    return _question("modal_degree", "tonal.modes",
                     f"In {key} {mode.title()}, spell scale degree {degree}.", answer,
                     [n.name_no_octave for n in notes if n.name_no_octave != answer],
                     f"{key} {mode.title()}: {' '.join(n.name_no_octave for n in notes[:7])}. "
                     f"Its characteristic color is {characteristic}, relative to parallel major.",
                     difficulty, rng, {"mode": "melody", "midis": [n.midi for n in notes], "tempo": 90})


@register("dominant_tendency", "theory", "V7: third versus seventh resolution")
def dominant_tendency(difficulty: float, rng: random.Random) -> Exercise:
    key = rng.choice(KEYS if difficulty >= 3 else KEYS[:2])
    mode = rng.choice(("major", "minor")) if difficulty >= 5 else "major"
    chord = roman_to_chord("V7", key, mode)
    tonic = roman_to_chord("I" if mode == "major" else "i", key, mode)
    third = rng.choice((True, False))
    source = chord.members[1 if third else 3]
    target = tonic.members[0 if third else 1]
    answer = target.name_no_octave
    return _question("dominant_tendency", "tonal.tendencies",
                     f"In {key} {mode}, V7 resolves to tonic. Where does its "
                     f"{'third (leading tone)' if third else 'chordal seventh'} {source.name_no_octave} "
                     "normally resolve in a strict same-voice resolution?", answer,
                     [n.name_no_octave for n in scale_notes(Note.parse(key + "4"),
                      "major" if mode == "major" else "harmonic_minor") if n.name_no_octave != answer],
                     f"The third of V7 rises to tonic (7→1); its seventh falls to the tonic third (4→3). "
                     f"Here {source.name_no_octave} resolves {'up' if third else 'down'} to {answer}. "
                     "An instructor may allow an inner-voice frustrated leading tone in specific voicings.",
                     difficulty, rng)


@register("applied_target", "theory", "Applied dominants and temporary leading tones")
def applied_target(difficulty: float, rng: random.Random) -> Exercise:
    key = rng.choice(KEYS)
    target = rng.choice(("V", "ii", "vi", "IV"))
    chord = roman_to_chord("V7/" + target, key, "major")
    answer = roman_to_chord(target, key, "major").root.name_no_octave
    return _question("applied_target", "tonal.tonicization",
                     f"In {key} major, V7/{target} contains {chord.members[1].name_no_octave} "
                     "as its temporary leading tone. To which root does it lead?", answer,
                     [n.name_no_octave for n in scale_notes(Note.parse(key + "4"), "major")
                      if n.name_no_octave != answer],
                     f"Read the slash as 'of': V7/{target} is the dominant seventh of {target}. "
                     f"Its third {chord.members[1].name_no_octave} rises by semitone to {answer}. "
                     "A local tonicization alone does not establish a modulation.", difficulty, rng)


@register("nonchord_tone", "theory", "Passing, neighbor, suspension, anticipation")
def nonchord_tone(difficulty: float, rng: random.Random) -> Exercise:
    tonic = Note.parse(rng.choice(KEYS) + "4")
    scale = scale_notes(tonic, "major")
    names = [n.name_no_octave for n in scale]
    cases = [
        (f"Over a held tonic triad, an unaccented {names[1]} connects {names[0]} up to {names[2]} by step.",
         "Passing tone", "It fills the gap between two different chord tones in the same direction."),
        (f"Over a held tonic triad, {names[0]} moves up to unaccented {names[1]} and back to {names[0]}.",
         "Neighbor tone", "It leaves a chord tone by step and returns to that same chord tone."),
        (f"{names[3]} is prepared in IV, tied into the accented onset of I, then resolves down to {names[2]}.",
         "Suspension", "Preparation → accented dissonance held across the harmony change → downward step."),
        (f"Just before V changes to I, unaccented {names[0]} arrives early and is repeated as I begins.",
         "Anticipation", "The next harmony's tone arrives early, before the harmony changes.")]
    prompt, answer, explanation = rng.choice(cases)
    return _question("nonchord_tone", "tonal.nonchord", prompt + " Identify the non-chord tone.",
                     answer, [c[1] for c in cases if c[1] != answer], explanation, difficulty, rng)


@register("chromatic_function", "theory", "Mixture, Neapolitan, augmented sixths")
def chromatic_function(difficulty: float, rng: random.Random) -> Exercise:
    key = rng.choice(KEYS)
    tonic = Note.parse(key + "4")
    case = rng.randrange(3)
    if case == 0:
        chord = roman_to_chord("iv", key, "major")
        notes = "–".join(n.name_no_octave for n in chord.members)
        answer = "Borrowed iv"
        prompt = f"In {key} major, {notes} is a minor subdominant. What is its source/function?"
        why = "Mixture borrows iv from the parallel minor; it does not by itself change the tonic."
    elif case == 1:
        root = transpose(tonic, 2, "m").name_no_octave
        answer = "Neapolitan sixth"
        prompt = f"In {key}, a major triad on {root} (flat 2) appears in first inversion as a predominant. Name it."
        why = "N6 is a major triad on lowered scale degree 2, usually first inversion, leading toward dominant."
    else:
        low = transpose(tonic, 6, "m").name_no_octave
        high = transpose(tonic, 4, "A").name_no_octave
        answer = "Augmented-sixth chord"
        prompt = f"In {key}, {low} (flat 6) and {high} (sharp 4) expand outward toward scale degree 5. Name the family."
        why = "The characteristic augmented sixth expands to an octave on scale degree 5; spelling shows direction."
    return _question("chromatic_function", "tonal.chromatic_predominants", prompt, answer,
                     [x for x in ("Borrowed iv", "Neapolitan sixth", "Augmented-sixth chord", "Secondary dominant")
                      if x != answer], why, difficulty, rng)


@register("modulation_evidence", "theory", "Tonicization versus modulation")
def modulation_evidence(difficulty: float, rng: random.Random) -> Exercise:
    key = rng.choice(KEYS)
    new = roman_to_chord("V", key, "major").root.name_no_octave
    established = rng.choice((True, False))
    prompt = (f"A passage begins in {key} major. " +
              (f"It pivots to {new} major, sustains its harmony, and closes a phrase with a PAC in {new}."
               if established else "V/V briefly colors V, then V7–I closes the phrase in the original key."))
    answer = "Modulation" if established else "Tonicization"
    return _question("modulation_evidence", "tonal.modulation", prompt + " Which reading fits this evidence?",
                     answer, [x for x in ("Modulation", "Tonicization", "Mode mixture", "No tonal center") if x != answer],
                     "A sustained new tonic supported by a phrase cadence supports modulation; "
                     "one applied dominant can tonicize a chord without changing the governing key.", difficulty, rng)


@register("tonal_phrase", "theory", "Cadences and phrase structure")
def tonal_phrase(difficulty: float, rng: random.Random) -> Exercise:
    case = rng.choice((
        ("Two phrases have similar beginnings. The first ends in a half cadence, the second in a PAC.",
         "Parallel period", "Related beginnings and weaker→stronger cadences support an antecedent–consequent period."),
        ("A two-measure basic idea is repeated, then fragments accelerate toward a cadence (2+2+4).",
         "Sentence", "Presentation is followed by continuation and cadential closure."),
        ("A phrase stops on V, with no following tonic resolution in that phrase.",
         "Half cadence", "A phrase ending on dominant is a half cadence; it leaves tonal motion open."),
        ("At a phrase ending, root-position V resolves to root-position I, with tonic in the soprano.",
         "Perfect authentic cadence", "Root positions plus tonic in soprano define a PAC in this tonal context.")))
    prompt, answer, why = case
    return _question("tonal_phrase", "tonal.phrases", prompt + " Identify the described pattern.", answer,
                     [x for x in ("Parallel period", "Sentence", "Half cadence", "Perfect authentic cadence")
                      if x != answer], why, difficulty, rng)
