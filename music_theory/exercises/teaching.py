"""Concept explanations and hints keyed by exercise type.

Shown when a learner answers incorrectly so that someone who does not yet know
the material gets a short, self-contained lesson - not just the right answer."""

from __future__ import annotations

_CONCEPTS: dict[str, str] = {
    "note_identification":
        "Notes sit on the lines and spaces of the staff. In treble clef the lines "
        "from bottom to top spell E-G-B-D-F and the spaces spell F-A-C-E; bass clef "
        "lines are G-B-D-F-A and spaces A-C-E-G. Find the reference and step up or "
        "down by line/space to name any note.",
    "interval_identification":
        "An interval has a number (count the letter names inclusively, so C up to E "
        "is a 3rd) and a quality (major, minor, perfect, augmented, diminished) set "
        "by the exact semitone distance. Major 3rd = 4 semitones, perfect 5th = 7, "
        "and so on.",
    "interval_construction":
        "To build an interval, first count letter names up from the start note for "
        "the number, then adjust the top note with accidentals so the semitone count "
        "matches the quality. A major 3rd is 4 semitones; a perfect 5th is 7.",
    "scale_identification":
        "Each scale type has a fixed pattern of whole and half steps. Major is "
        "W-W-H-W-W-W-H; natural minor is W-H-W-W-H-W-W. Listen for where the half "
        "steps fall and whether the 3rd above the tonic sounds major or minor.",
    "scale_spelling":
        "Spell a scale using each letter name once in order, adding sharps or flats "
        "to match the step pattern (major = W-W-H-W-W-W-H). Never mix, e.g., F# and "
        "Gb in the same scale - use consecutive letters.",
    "key_signature_identification":
        "Sharps are added in the order F C G D A E B; the last sharp is the leading "
        "tone, so the key is a half step above it. Flats go B E A D G C F; the "
        "second-to-last flat names the major key. Relative minors share the "
        "signature a minor 3rd below.",
    "triad_quality":
        "A triad stacks two 3rds. Major = major 3rd + minor 3rd (e.g., C-E-G); minor "
        "= minor 3rd + major 3rd; diminished = two minor 3rds; augmented = two major "
        "3rds. The quality of the lower 3rd and the size of the 5th tell them apart.",
    "seventh_quality":
        "A seventh chord adds a 3rd above a triad. Common types: major 7th "
        "(maj triad + major 7th), dominant 7th (maj triad + minor 7th), minor 7th "
        "(min triad + minor 7th), half-diminished (dim triad + minor 7th), and fully "
        "diminished (dim triad + diminished 7th).",
    "triad_spelling":
        "Pick the root, then stack a 3rd and a 5th using letter names (root, skip a "
        "letter, skip again). Adjust accidentals for quality: major = 4+3 semitones, "
        "minor = 3+4, diminished = 3+3, augmented = 4+4.",
    "chord_inversion":
        "Figured bass names the chord tone in the bass. Triads: root position (5/3), "
        "first inversion = 6, second inversion = 6/4. Sevenths: 7, 6/5, 4/3, 4/2 as "
        "the root, 3rd, 5th, or 7th is in the bass.",
    "roman_numeral_analysis":
        "Roman numerals show a chord's scale-degree root and quality: uppercase = "
        "major, lowercase = minor, ° = diminished. In major the diatonic chords are "
        "I ii iii IV V vi vii°. Find the root's scale degree, then check the quality.",
    "roman_numeral_build":
        "Translate the numeral to a scale degree (V = the 5th degree), build the "
        "triad on that degree using the key's notes, and let the numeral's case set "
        "the quality (uppercase major, lowercase minor).",
    "interval_recognition":
        "Tie each interval to a familiar tune: perfect 4th = 'Here Comes the Bride', "
        "perfect 5th = 'Twinkle Twinkle', major 3rd = bright/happy, minor 3rd = "
        "darker. Compare the two pitches and judge how far apart they sound.",
    "chord_quality_ear":
        "Major chords sound bright and stable, minor sounds darker, diminished feels "
        "tense and unstable, and augmented sounds dreamlike. Focus on the 3rd above "
        "the bass to decide major vs. minor.",
    "scale_mode_ear":
        "Sing from the tonic and listen for the colour notes: a lowered 3rd means "
        "minor/Dorian/Phrygian, a raised 4th suggests Lydian, a lowered 7th suggests "
        "Mixolydian or Dorian. The pattern of half steps gives each mode its flavour.",
    "melodic_dictation":
        "Hold the tonic in your ear, then track each note as a scale step or leap up "
        "or down from the last. Notate the contour first, then refine exact pitches; "
        "replay as needed and check that it resolves back toward the tonic.",
    "rhythmic_dictation":
        "Feel the steady beat and subdivide it. Decide whether each sound lands on a "
        "beat or between beats, and how many beats it lasts (quarter = 1, eighth = "
        "1/2). The durations in one bar must add up to the time signature.",
    "harmonic_dictation":
        "Listen to the bass line and the function of each chord. Most phrases move "
        "tonic -> predominant (IV/ii) -> dominant (V) -> tonic. Identify the bass "
        "scale degree, then the chord quality above it.",
    "cadence_ear":
        "Cadences are how phrases end. Authentic = V->I (final), Half = ends on V "
        "(unfinished), Plagal = IV->I ('Amen'), Deceptive = V->vi (surprise). Listen "
        "to the last two chords and whether it sounds resolved.",
    "error_detection":
        "Read the score while you listen and follow note by note. The wrong note "
        "will clash with the printed pitch - usually a step too high or low. Pinpoint "
        "exactly where the sound diverges from the page.",
    "play_note":
        "On the keyboard, the two-black-key group sits around C-D-E and the "
        "three-black-key group around F-G-A-B. C is just left of the two black keys; "
        "use that landmark to find any note.",
    "play_interval":
        "Play the start note, then count up by the interval: count letter names for "
        "the number and semitones for the quality (perfect 5th = 7 semitones up). "
        "Press both keys to confirm the distance.",
    "play_triad":
        "Build the triad by stacking 3rds from the root: root, skip a key to the "
        "3rd, skip again to the 5th. Adjust for quality (major = 4 then 3 semitones, "
        "minor = 3 then 4).",
    "play_scale":
        "Play the scale one letter at a time following its step pattern (major = "
        "W-W-H-W-W-W-H). Watch where the half steps fall - between degrees 3-4 and "
        "7-8 in major.",
    "pcset_normal_form":
        "Normal form is the most compact ordering of a pitch-class set within an "
        "octave. List the pcs, try each rotation, and pick the one spanning the "
        "smallest interval from first to last (break ties by packing to the left).",
    "pcset_prime_form":
        "Prime form is the normal form transposed to start on 0, compared with its "
        "inversion, choosing the most left-packed version. It identifies the set "
        "class regardless of transposition or inversion.",
    "pcset_interval_vector":
        "The interval-class vector counts how many times each interval class (1-6) "
        "appears between all pairs of pcs in the set. Tally every pair, reducing "
        "intervals larger than 6 to their complement.",
    "forte_identification":
        "Forte names label set classes by cardinality and ordinal (e.g., 3-11 is the "
        "major/minor triad). Reduce the set to prime form, then match it to its Forte "
        "number.",
    "set_transposition":
        "Tn adds n to every pc (mod 12); TnI inverts (12 - pc) then adds n. Apply the "
        "operation to each pitch class individually and reduce mod 12.",
    "row_form_identification":
        "A twelve-tone row has four forms: Prime (P), Inversion (I, flipped "
        "intervals), Retrograde (R, P backwards), and Retrograde-Inversion (RI). "
        "Compare the given series' intervals to P0 to identify the form and "
        "transposition level.",
    "row_matrix_lookup":
        "The 12x12 matrix holds every row form: P forms read left-to-right, I forms "
        "top-to-bottom, R right-to-left, RI bottom-to-top. Build it from P0 and its "
        "inversion, then read off the requested form.",
    "neo_riemannian":
        "The three PLR moves connect triads by common tones: P swaps major/minor "
        "(C<->Cm), L moves the root by a half step (C<->Em), R moves the 5th "
        "(C<->Am). Apply each letter in turn to transform the triad.",
}

_HINTS: dict[str, str] = {
    "note_identification": "Use a clef landmark (treble lines E-G-B-D-F) and step to the note.",
    "interval_identification": "Count letter names for the number, then check the semitones.",
    "interval_construction": "Count letters up for the number; adjust the top note's accidental.",
    "triad_quality": "Listen to the lower 3rd: major sounds bright, minor sounds dark.",
    "seventh_quality": "Identify the triad first, then the size of the 7th above the root.",
    "roman_numeral_analysis": "Find the chord's root, then its scale degree in the key.",
    "interval_recognition": "Match it to a song you know (5th = Twinkle Twinkle).",
    "chord_quality_ear": "Focus on the 3rd: major = bright, minor = dark, dim = tense.",
    "cadence_ear": "Listen to the final two chords - does it sound finished?",
    "melodic_dictation": "Track each note as a step or leap from the previous one.",
    "key_signature_identification": "Last sharp = leading tone; 2nd-to-last flat = the key.",
}


def concept_for(etype: str) -> str:
    """Return a short teaching explanation for an exercise type."""
    return _CONCEPTS.get(etype, "")


def hint_for(etype: str) -> str:
    """Return a brief pre-answer hint for an exercise type, if available."""
    return _HINTS.get(etype, "")
