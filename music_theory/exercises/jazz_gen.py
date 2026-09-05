"""Jazz harmony, listening and keyboard drills following tonal fundamentals."""
from .registry import register
from .base import Exercise, InputMode
from ._util import choices_from
from ..theory.pitch import Note
from ..theory.jazz import ii_v_i, shell_voicings

KEYS = ("C", "F", "G", "Bb", "D", "Eb", "A", "Ab")


def _context(difficulty, rng):
    return Note.parse(rng.choice(KEYS[:3] if difficulty < 4 else KEYS) + "4")


def _choice(etype, skill, prompt, answer, options, explanation, difficulty, rng, play=None, domain="theory"):
    return Exercise(skill_id=skill, etype=etype, domain=domain, prompt=prompt,
                    input_mode=InputMode.MULTIPLE_CHOICE, answer=answer,
                    choices=choices_from(answer, options, rng, k=4), explanation=explanation,
                    teach=explanation, difficulty=difficulty, play=play)


@register("jazz_ii_v_i", "theory", "Jazz ii–V–I chord functions")
def jazz_ii_v_i(difficulty, rng):
    tonic = _context(difficulty, rng)
    progression = ii_v_i(tonic, minor=difficulty >= 5 and rng.choice([True, False]))
    index = rng.randrange(3)
    chord = progression[index]
    notes = " ".join(n.name_no_octave for n in chord.notes)
    return _choice("jazz_ii_v_i", "jazz.progressions", f"In this ii–V–I family in {tonic.name_no_octave}, what is the function of {notes}?",
                   chord.label, ["ii7", "iiø7", "V7", "Imaj7", "i7", "IVmaj7"],
                   "The progression is " + " → ".join(c.label + " (" + " ".join(n.name_no_octave for n in c.notes) + ")" for c in progression),
                   difficulty, rng)


@register("jazz_guide_tones", "theory", "Jazz guide tones: thirds and sevenths")
def jazz_guide_tones(difficulty, rng):
    chord = rng.choice(ii_v_i(_context(difficulty, rng)))
    answer = " & ".join(n.name_no_octave for n in chord.guides)
    return _choice("jazz_guide_tones", "jazz.guides", "Which pair is the third and seventh of " + " ".join(n.name_no_octave for n in chord.notes) + "?",
                   answer, [" & ".join(chord.notes[i].name_no_octave for i in pair) for pair in ((0, 2), (0, 3), (1, 2))],
                   f"The guide tones are {answer}. They communicate the quality and connect adjacent harmonies with small motions.", difficulty, rng)


@register("jazz_tritone_sub", "theory", "Tritone substitutions")
def jazz_tritone_sub(difficulty, rng):
    tonic = _context(difficulty, rng)
    normal = ii_v_i(tonic)[1]
    substitute = ii_v_i(tonic, substitute=True)[1]
    answer = substitute.notes[0].name_no_octave + "7"
    return _choice("jazz_tritone_sub", "jazz.substitution", f"Which dominant seventh can replace {normal.notes[0].name_no_octave}7 as a tritone substitute resolving toward {tonic.name_no_octave}?",
                   answer, [tonic.name_no_octave + "7", normal.notes[0].name_no_octave + "maj7", normal.notes[0].name_no_octave + "m7"],
                   f"{answer} is a tritone away from the original dominant root. Its third and seventh share the original guide-tone pitch classes, with different spelling and roles.", difficulty, rng)


@register("jazz_progression_ear", "aural", "Hear standard and substituted ii–V–I")
def jazz_progression_ear(difficulty, rng):
    substitute = rng.choice([False, True])
    chords = ii_v_i(_context(difficulty, rng), substitute=substitute)
    answer = "Tritone substitute" if substitute else "Standard ii–V–I"
    return _choice("jazz_progression_ear", "aural.jazz", "Listen to the three chords. Does the middle bass use the standard dominant or a tritone substitute?",
                   answer, ["Standard ii–V–I", "Tritone substitute"],
                   "Bass motion distinguishes V from ♭II; the third/seventh guide tones can sound closely related.", difficulty, rng,
                   {"mode": "harmonic", "chords": [[n.midi for n in c] for c in shell_voicings(chords)], "tempo": 75}, "aural")


@register("play_jazz_shell", "piano", "Play root, third and seventh")
def play_jazz_shell(difficulty, rng):
    chord = rng.choice(ii_v_i(_context(difficulty, rng)))
    tones = [chord.notes[0], *chord.guides]
    return Exercise(skill_id="piano.jazz", domain="piano", etype="play_jazz_shell",
                    prompt=f"Play a shell for {' '.join(n.name_no_octave for n in chord.notes)}: root, third and seventh, in any octave.",
                    input_mode=InputMode.PIANO, answer=[n.midi for n in tones], tags={"match": "pc"},
                    difficulty=difficulty, explanation="Shell tones: " + " ".join(n.name_no_octave for n in tones),
                    teach="A shell retains the root, third and seventh. The fifth can be omitted when it is not needed to distinguish an altered chord.")
