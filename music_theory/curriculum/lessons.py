"""Built-in mini-lessons: every skill teaches its concept before drilling it.

Each skill maps to a short sequence of pages (text, optional audio example,
optional staff illustration) shown the first time the skill appears in Learn
mode - so a learner who has never met the concept gets taught it, Duolingo
style, instead of being quizzed cold. The same lessons can be re-read at any
time from the Learn screen.

Page fields:
* ``title``/``body`` - the teaching text (body may use simple HTML).
* ``play``  - an audio spec understood by :func:`exercises.base.render_play`.
* ``staff`` - ``{"clef": ..., "notes": "C4 E4 G4", "key_sig": int}`` shown on
  a staff widget (notes are space-separated names, parsed lazily).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class LessonPage:
    title: str
    body: str
    play: Optional[dict] = None
    staff: Optional[dict] = None


def _P(title: str, body: str, play: Optional[dict] = None,
       staff: Optional[dict] = None) -> LessonPage:
    return LessonPage(title, body, play, staff)


def _melody(*midis: int, tempo: int = 100, beats: float = 1.0) -> dict:
    return {"mode": "melody", "midis": list(midis), "tempo": tempo, "beats": beats}


def _chord(*midis: int) -> dict:
    return {"mode": "chord", "midis": list(midis)}


def _chords(chords: list[list[int]], tempo: int = 76) -> dict:
    return {"mode": "harmonic", "chords": chords, "tempo": tempo, "beats": 2.0}


LESSONS: dict[str, list[LessonPage]] = {
    # ================= Beginner =================
    "fund.note_names": [
        _P("The staff",
           "Music is written on a <b>staff</b> of five lines and four spaces. "
           "Each line and space holds one letter name from A to G; after G the "
           "letters start over. Moving up a line-or-space = the next letter."),
        _P("Treble clef landmarks",
           "In <b>treble clef</b> the lines, bottom to top, are E-G-B-D-F "
           "(<i>Every Good Boy Does Fine</i>) and the spaces spell F-A-C-E. "
           "Find one landmark, then count lines and spaces to name any note.",
           staff={"clef": "treble", "notes": "E4 G4 B4 D5 F5"}),
        _P("Bass clef landmarks",
           "In <b>bass clef</b> the lines are G-B-D-F-A (<i>Good Boys Do Fine "
           "Always</i>) and the spaces are A-C-E-G. Middle C sits on a small "
           "ledger line above the bass staff and below the treble staff.",
           staff={"clef": "bass", "notes": "G2 B2 D3 F3 A3"}),
    ],
    "aural.intervals": [
        _P("What is an interval?",
           "An <b>interval</b> is the distance between two pitches. Small "
           "intervals sound like neighbouring steps; large ones sound like "
           "leaps. Train your ear by comparing every interval you hear to a "
           "song you already know."),
        _P("The perfect fifth",
           "This is a <b>perfect 5th</b> - the open, stable sound that starts "
           "<i>Twinkle Twinkle Little Star</i> (and the Star Wars theme).",
           play=_melody(60, 67)),
        _P("Major and minor thirds",
           "The <b>major 3rd</b> sounds bright (first two notes of <i>Oh, when "
           "the Saints</i>); the <b>minor 3rd</b> sounds darker (<i>Greensleeves</i>). "
           "Listen to both back to back: major 3rd, then minor 3rd.",
           play=_melody(60, 64, 60, 63, tempo=80)),
    ],
    "aural.melodic_dictation": [
        _P("What dictation trains",
           "<b>Melodic dictation</b> = hearing a melody and writing it down. "
           "It is the single best exercise for connecting your ear to notation. "
           "You will always be given the key and the first note."),
        _P("Strategy: contour first",
           "Don't chase exact pitches immediately. First sketch the <b>contour</b>: "
           "does each note step up, step down, leap, or repeat? Then pin each note "
           "to a scale degree, keeping the tonic humming in your head."),
        _P("Try the idea",
           "Listen: this short melody steps up from the tonic and comes back "
           "down (do-re-mi-re-do). Hearing scale degrees, not letter names, "
           "is the skill.",
           play=_melody(60, 62, 64, 62, 60, tempo=92)),
    ],
    "piano.find_notes": [
        _P("Keyboard geography",
           "The black keys alternate in groups of <b>two</b> and <b>three</b>. "
           "C is always the white key just left of the two-black-key group; "
           "F is just left of the three-black-key group."),
        _P("Octaves",
           "The pattern repeats every 12 keys - one <b>octave</b>. Middle C "
           "(C4) sits near the middle of the keyboard. From any C, the white "
           "keys upward are C-D-E-F-G-A-B.",
           play=_melody(60, 62, 64, 65, 67, 69, 71, 72, tempo=140, beats=0.5)),
    ],
    "aural.rhythmic_dictation": [
        _P("Feel the beat",
           "Rhythm dictation starts with the steady <b>beat</b>. Tap it. Every "
           "sound you hear either lands on a beat or between beats. A quarter "
           "note = 1 beat, an eighth = half a beat, a half note = 2 beats."),
        _P("Subdivide",
           "Mentally split each beat in two ('1-and-2-and...'). Decide where each "
           "attack lands and how long it lasts; the durations in a bar must add "
           "up to the meter (4 beats in 4/4).",
           play={"mode": "sequence", "items": [(67, 1.0), (67, 0.5), (67, 0.5),
                                               (67, 1.0), (67, 1.0)], "tempo": 96}),
    ],

    # ================= Early =================
    "fund.intervals": [
        _P("Number + quality",
           "A written interval has two parts: a <b>number</b> (count letter "
           "names inclusively: C up to E = C, D, E = a 3rd) and a <b>quality</b> "
           "(major, minor, perfect, augmented, diminished)."),
        _P("Quality = exact semitones",
           "Each number+quality pairs with an exact semitone count: minor 2nd = 1, "
           "major 2nd = 2, minor 3rd = 3, major 3rd = 4, perfect 4th = 5, tritone = 6, "
           "perfect 5th = 7, minor 6th = 8, major 6th = 9, minor 7th = 10, "
           "major 7th = 11, octave = 12."),
        _P("Perfect vs major/minor",
           "Unisons, 4ths, 5ths and octaves are <b>perfect</b> - they have one "
           "natural size. 2nds, 3rds, 6ths and 7ths come in <b>major/minor</b> "
           "pairs (minor = one semitone smaller). One semitone beyond major or "
           "perfect = augmented; one below minor or perfect = diminished."),
        _P("Worked example",
           "C up to A: letters C-D-E-F-G-A = a 6th. Count semitones: 9, which "
           "matches a <b>major 6th</b>. To build a minor 6th instead, lower the "
           "top note one semitone: C-Ab.",
           play=_melody(60, 69, 60, 68, tempo=84)),
    ],
    "scales.key_signatures": [
        _P("Why key signatures exist",
           "A <b>key signature</b> collects the sharps or flats a key always "
           "uses, so they're written once instead of on every note. Each major "
           "key has exactly one signature, shared with its relative minor."),
        _P("The order of sharps",
           "Sharps always appear in the order <b>F C G D A E B</b> "
           "(<i>Father Charles Goes Down And Ends Battle</i>). The <b>last sharp "
           "is the leading tone</b>: go up a half step from it to name the major "
           "key. Two sharps (F#, C#) → D major."),
        _P("The order of flats",
           "Flats appear in the reverse order: <b>B E A D G C F</b>. The "
           "<b>second-to-last flat names the key</b>: three flats (Bb, Eb, Ab) → "
           "Eb major. (F major, with one flat, you simply memorize.) The relative "
           "minor is a minor 3rd below the major tonic: Eb major ↔ C minor."),
    ],
    "scales.spell": [
        _P("The major scale pattern",
           "A <b>major scale</b> is a fixed pattern of whole (W) and half (H) "
           "steps: <b>W-W-H-W-W-W-H</b>. Start on any note, apply the pattern, "
           "and you have its major scale.",
           play=_melody(60, 62, 64, 65, 67, 69, 71, 72, tempo=132, beats=0.5)),
        _P("One letter each",
           "Spelling rule: use <b>each letter name exactly once</b> per octave, "
           "adding accidentals as the pattern requires. D major = D E F# G A B C# D. "
           "Never mix sharps and flats in one scale."),
        _P("Minor scales",
           "Natural minor = W-H-W-W-H-W-W (the major scale starting on its 6th "
           "degree). <b>Harmonic minor</b> raises the 7th (creating its signature "
           "augmented 2nd); <b>melodic minor</b> raises 6 and 7 going up and "
           "reverts coming down.",
           play=_melody(57, 59, 60, 62, 64, 65, 68, 69, tempo=132, beats=0.5)),
    ],
    "scales.identify": [
        _P("Hearing the pattern on paper",
           "To identify a written scale, find where the <b>half steps</b> fall. "
           "Between degrees 3-4 and 7-8 → major. A lowered 3rd points to a minor "
           "form; then check degrees 6 and 7 to tell natural, harmonic, melodic."),
        _P("The church modes",
           "Modes are rotations of the major scale: starting on its 2nd degree "
           "gives <b>Dorian</b>, 3rd <b>Phrygian</b>, 4th <b>Lydian</b>, 5th "
           "<b>Mixolydian</b>, 6th <b>Aeolian</b> (natural minor), 7th <b>Locrian</b>. "
           "Identify the tonic, then match its interval pattern."),
    ],
    "chords.triad_quality": [
        _P("Stacking thirds",
           "A <b>triad</b> is three notes stacked in 3rds: root, 3rd, 5th. The "
           "sizes of those 3rds set the <b>quality</b>: major = M3+m3, minor = "
           "m3+M3, diminished = m3+m3, augmented = M3+M3."),
        _P("Hear the four qualities",
           "Major sounds bright and settled; minor darker; diminished tense and "
           "shrunken; augmented dreamlike and unresolved. Listen: C major, C minor, "
           "C diminished, C augmented.",
           play=_chords([[60, 64, 67], [60, 63, 67], [60, 63, 66], [60, 64, 68]],
                        tempo=60)),
        _P("Spot the 5th",
           "Major and minor share a perfect 5th - only the 3rd differs. If the "
           "5th itself sounds shrunken (diminished) or stretched (augmented), "
           "the quality is no longer major/minor. Check 3rd first, then 5th."),
    ],
    "chords.triad_spell": [
        _P("Spelling triads",
           "Pick the root, skip a letter for the 3rd, skip again for the 5th: "
           "every triad on C uses C-E-G letters. Then add accidentals for the "
           "quality: major = 4+3 semitones, minor = 3+4, dim = 3+3, aug = 4+4."),
        _P("Worked example",
           "Eb minor: letters Eb-Gb-Bb. Check: Eb→Gb = 3 semitones (minor 3rd), "
           "Gb→Bb = 4 (major 3rd). Letters first, accidentals second - that's "
           "what keeps F# and Gb from sneaking into the same chord.",
           play=_chord(63, 66, 70)),
    ],
    "piano.intervals": [
        _P("Intervals under your fingers",
           "On the keyboard an interval is a number of half steps (count every "
           "key, black and white). Major 3rd = 4 half steps, perfect 4th = 5, "
           "perfect 5th = 7, octave = 12."),
        _P("Shape shortcuts",
           "5ths from white keys are white-to-white with one exception (B→F# "
           "needs a black key). Octaves are the same letter. Build the habit of "
           "counting half steps until shapes become automatic.",
           play=_melody(60, 67, 60, 72, tempo=84)),
    ],
    "piano.scales": [
        _P("Playing scales",
           "Play scales one letter at a time following W-W-H-W-W-W-H. On the "
           "keyboard a whole step skips one key; a half step is the very next "
           "key (black or white)."),
        _P("Where the black keys go",
           "C major is all white. G major needs F#; F major needs Bb. Each new "
           "sharp key adds the next sharp in F-C-G-D-A-E-B order - the keyboard "
           "makes the circle of fifths visible.",
           play=_melody(67, 69, 71, 72, 74, 76, 78, 79, tempo=132, beats=0.5)),
    ],
    "aural.chord_quality": [
        _P("Chord color",
           "Each triad quality has a distinct <b>color</b>: major bright, minor "
           "dark, diminished tense, augmented floating. Your ear learns colors "
           "faster than note-by-note analysis - trust the gestalt."),
        _P("Focus on the third",
           "When unsure between major and minor, hum the root, then the note a "
           "3rd above. A bright, wide 3rd = major; a darker, narrow 3rd = minor. "
           "Listen: C major then C minor.",
           play={"mode": "harmonic", "chords": [[60, 64, 67], [60, 63, 67]], "tempo": 60}),
        _P("Sevenths add a layer",
           "Seventh chords stack one more 3rd. Dominant 7th = major triad + minor "
           "7th (bluesy, wants to resolve); major 7th = dreamy; minor 7th = mellow; "
           "half-diminished = anxious; fully diminished = maximal tension.",
           play={"mode": "harmonic", "chords": [[60, 64, 67, 70], [60, 64, 67, 71],
                                                [60, 63, 67, 70]], "tempo": 60}),
    ],
    "aural.scales": [
        _P("Scale flavors",
           "Every scale/mode has a signature 'flavor note'. Compare each degree "
           "to the major scale: lowered 3rd → minor family; raised 4th → Lydian; "
           "lowered 7th with major 3rd → Mixolydian; lowered 2nd → Phrygian."),
        _P("Listen for the tonic",
           "Modes share the same notes but a different home base. Sing the tonic "
           "while the scale plays; the relationship of each note to that anchor "
           "is what tells Dorian from natural minor (Dorian's 6th is raised).",
           play=_melody(62, 64, 65, 67, 69, 71, 72, 74, tempo=132, beats=0.5)),
    ],

    # ================= Intermediate =================
    "chords.seventh_quality": [
        _P("Five common sevenths",
           "Memorize five: <b>major 7th</b> (maj triad + M7), <b>dominant 7th</b> "
           "(maj triad + m7), <b>minor 7th</b> (min triad + m7), <b>half-diminished</b> "
           "(dim triad + m7), <b>fully diminished</b> (dim triad + d7)."),
        _P("Triad first, then the 7th",
           "Identify the triad quality inside the chord, then measure the 7th "
           "above the root. Both pieces of evidence together leave only one "
           "answer. G7 = G-B-D (major) + F (minor 7th) → dominant 7th."),
        _P("Where they live in a key",
           "In major: Imaj7, ii m7, iii m7, IVmaj7, V7, vi m7, viiø7. The "
           "dominant 7th occurs naturally <i>only on scale degree 5</i> - hearing "
           "one usually locates the dominant for you."),
    ],
    "chords.inversions": [
        _P("Bass note ≠ root",
           "A chord is <b>inverted</b> when a note other than the root is in the "
           "bass. 3rd in the bass = first inversion; 5th = second inversion; "
           "7th (for sevenths) = third inversion."),
        _P("Figured bass numbers",
           "The figures name intervals above the bass. Triads: root = 5/3 (left "
           "blank), 1st inv = 6, 2nd inv = 6/4. Sevenths: 7, 6/5, 4/3, 4/2 in "
           "root through third inversion."),
        _P("Why inversions matter",
           "Inversions smooth the bass line and control stability: root position "
           "is solid, 6 chords are lighter, 6/4 chords are unstable and need "
           "resolution (the cadential 6/4 → V is the classic case)."),
    ],
    "harmony.roman_numerals": [
        _P("Chords as scale degrees",
           "Roman-numeral analysis names each chord by the <b>scale degree of its "
           "root</b>: I, ii, iii, IV, V, vi, vii°. Uppercase = major, lowercase = "
           "minor, ° = diminished, + = augmented."),
        _P("The diatonic palette",
           "In any major key: I ii iii IV V vi vii°. In minor (with the raised "
           "leading tone): i ii° III iv V VI vii°. Note V is major in both - the "
           "raised 7th creates the pull to tonic."),
        _P("Function: T - PD - D",
           "Chords act in three families: <b>tonic</b> (I, vi) = home, "
           "<b>predominant</b> (IV, ii) = departure, <b>dominant</b> (V, vii°) = "
           "tension that resolves home. Most phrases cycle T → PD → D → T.",
           play=_chords([[48, 60, 64, 67], [50, 57, 65, 69], [43, 55, 62, 67],
                         [48, 60, 64, 67]])),
        _P("How to analyze",
           "1) Find the key. 2) Stack the chord in 3rds to find its root. "
           "3) Count the root's scale degree. 4) Check quality against the "
           "case/symbol. Add figures for inversions (V6, ii6/5...)."),
    ],
    "harmony.roman_build": [
        _P("From numeral to notes",
           "Reverse the analysis: V in D major → 5th degree is A → spell a major "
           "triad on A (A-C#-E). The key signature does most of the accidental "
           "work for you."),
        _P("Applied figures",
           "Figures transfer too: V6/5 in C = G7 in first inversion = B in the "
           "bass. Minor keys: remember to raise the leading tone for V and vii° "
           "(E major chord in A minor uses G#).",
           play=_chords([[47, 62, 65, 67], [48, 60, 64, 72]])),
    ],
    "piano.chords": [
        _P("Triads under the hand",
           "Root position triads sit on alternating keys - play root, skip, 3rd, "
           "skip, 5th. Practice major and minor on every white-key root before "
           "adding accidentals."),
        _P("Inversions on keyboard",
           "Move the bottom note up an octave to invert: C-E-G → E-G-C (1st inv) "
           "→ G-C-E (2nd inv). Inversions keep your hand close when changing "
           "chords - the secret of smooth accompaniment.",
           play={"mode": "harmonic", "chords": [[60, 64, 67], [64, 67, 72],
                                                [67, 72, 76]], "tempo": 84}),
    ],
    "aural.cadences": [
        _P("Phrase punctuation",
           "A <b>cadence</b> is how a phrase ends. Authentic (V→I) = period. "
           "Half (ends on V) = comma. Plagal (IV→I) = the 'Amen'. Deceptive "
           "(V→vi) = the plot twist."),
        _P("Hear V → I",
           "The authentic cadence: tension, then home. The bass falls a 5th and "
           "the leading tone resolves up. This is the strongest closure in tonal "
           "music.",
           play=_chords([[43, 55, 62, 67], [48, 60, 64, 72]])),
        _P("Hear the deceptive move",
           "Deceptive: the V chord promises I but lands on vi - same two opening "
           "chords, different ending. Compare authentic, then deceptive.",
           play=_chords([[43, 55, 62, 67], [48, 60, 64, 72],
                         [43, 55, 62, 67], [45, 57, 60, 64]])),
    ],
    "aural.error_detection": [
        _P("Score vs sound",
           "You'll see a printed melody and hear a performance with <b>one wrong "
           "note</b>. Read along while listening, note by note, like proofreading "
           "against an original."),
        _P("Strategy",
           "Sing the printed line in your head <i>before</i> playback, then let any "
           "mismatch jump out. The wrong note is usually a step or two off - it "
           "clashes with your inner expectation more than with the chord."),
    ],
    "counterpoint.species": [
        _P("What counterpoint teaches",
           "<b>Species counterpoint</b> trains two melodies to be beautiful "
           "together. It's the foundation of voice leading: every rule exists to "
           "keep both lines independent and singable."),
        _P("First species (1:1)",
           "One note against each note of the given line (the <i>cantus firmus</i>). "
           "Use consonances only (unison, 3rd, 5th, 6th, octave). Begin and end on "
           "perfect consonances; approach the final by step."),
        _P("Parallel rule",
           "Never move into a perfect 5th or octave in <b>parallel</b> (both "
           "voices same direction) - it collapses two voices into one. Contrary "
           "motion is your best friend."),
        _P("Second & third species",
           "Second species: two notes against one - passing tones on weak beats "
           "introduce controlled dissonance. Third species: four against one - "
           "more passing/neighbour figuration, same logic."),
        _P("Fourth & fifth species",
           "Fourth species: syncopation - dissonant <b>suspensions</b> prepared "
           "on consonances and resolved down by step (7-6, 4-3). Fifth species "
           "('florid') combines everything. Now study real Palestrina and Bach!"),
    ],

    # ================= Advanced =================
    "aural.harmonic_dictation": [
        _P("Hearing progressions",
           "Harmonic dictation = identifying a chord progression by ear. Anchor "
           "on two things: the <b>bass line</b> (sing it) and the <b>function</b> "
           "of each sonority (tonic / predominant / dominant)."),
        _P("Bass first",
           "The bass tells you most of the story: scale degree 1 → I, degree 4 → "
           "IV or ii6, degree 5 → V, degree 6 after V → deceptive. Identify bass "
           "degrees, then refine the quality above them.",
           play=_chords([[48, 60, 64, 67], [53, 57, 65, 69], [43, 55, 62, 67],
                         [48, 60, 64, 72]])),
        _P("Listen in chunks",
           "Progressions move in formulas: I-IV-V-I, I-vi-IV-V, ii6-V-I. Learn "
           "the formulas as units and dictation becomes recognizing patterns, "
           "not decoding chords one at a time."),
    ],
    "aural.multipart": [
        _P("From one line to the whole texture",
           "You can already dictate a melody and identify progressions. "
           "<b>Multi-part dictation</b> merges those skills: transcribe every "
           "voice of a 2-4 voice texture - the way Bach heard, and how modern "
           "ears like Jacob Collier's pick apart dense harmony."),
        _P("Outer voices first",
           "The <b>soprano</b> is the most exposed line; the <b>bass</b> anchors "
           "the harmony. Get those two first - they are also the pair that "
           "defines the counterpoint. Listen: two voices moving in 3rds and 6ths.",
           play=_chords([[48, 64], [50, 65], [52, 67], [53, 69]], tempo=72)),
        _P("Infer, then verify the inner voices",
           "Once you have the outer voices, the harmony is usually implied. "
           "Inner voices fill remaining chord tones with the <i>smallest possible "
           "motion</i> - mostly repeating or stepping. Predict, then replay to "
           "verify each prediction."),
        _P("Focused listening",
           "Replay and follow ONE voice all the way through, singing along. "
           "Rotating your attention voice by voice is a trainable skill - it is "
           "the core of professional transcription. Start with 2 voices; the "
           "exercise grows to 3 and 4 as you improve."),
    ],
    "harmony.chromatic": [
        _P("Beyond the diatonic palette",
           "<b>Chromatic harmony</b> borrows notes from outside the key for "
           "color and direction: applied dominants, modal mixture, the Neapolitan "
           "and augmented-sixth chords."),
        _P("Applied (secondary) dominants",
           "Any major or minor chord can be preceded by <i>its own</i> dominant: "
           "V/V (in C: D major) leads to V. Look for accidentals that create a "
           "leading tone to a non-tonic chord.",
           play=_chords([[48, 60, 64, 67], [50, 57, 66, 69], [43, 55, 62, 67],
                         [48, 60, 64, 72]])),
        _P("Mixture and the Neapolitan",
           "<b>Mixture</b> borrows from the parallel minor (bVI, bIII, iv in "
           "major). The <b>Neapolitan</b> (bII, usually in first inversion: N6) "
           "is a dramatic predominant - a major triad on the lowered 2nd degree."),
        _P("Augmented sixth chords",
           "It+6, Fr+6, Ger+6 all stretch an augmented 6th around scale degree "
           "5: b6 below, #4 above, resolving outward to an octave on V. They are "
           "the most directional predominants in tonal music.",
           play=_chords([[44, 60, 66], [43, 59, 67]], tempo=66)),
    ],
    "harmony.part_writing": [
        _P("Four independent singers",
           "SATB writing combines <b>soprano, alto, tenor, and bass</b>. Keep each "
           "voice in range and in order. Soprano-alto and alto-tenor normally stay "
           "within an octave; tenor-bass may be wider. Crossing changes voice order; "
           "overlap moves a voice beyond an adjacent voice's previous position."),
        _P("Build the chord, then choose the doubling",
           "Include the intended chord members and inversion before optimizing motion. "
           "Root-position triads usually double the root; six-four chords double the "
           "bass/fifth; first-inversion diminished triads double their bass/third. "
           "Never double an active leading tone or chordal seventh."),
        _P("Motion and forbidden parallels",
           "Retain common tones and prefer steps. Contrary and oblique motion preserve "
           "independence. The same two voices may not move in similar motion through "
           "consecutive perfect unisons, fifths, or octaves, including compounds. "
           "Upper-voice parallel fourths are allowed by Common Practice but can be "
           "forbidden by a stricter instructor profile.",
           play=_chords([[48, 60, 64, 67], [50, 59, 62, 67], [43, 59, 62, 67],
                         [48, 60, 64, 67]], tempo=72)),
        _P("Directed tones and cadences",
           "A functional leading tone normally rises to tonic, and a chordal seventh "
           "normally falls by step. A perfect authentic cadence needs root-position "
           "V-I with scale degree 1 in the soprano; imperfect authentic, half, deceptive, "
           "and plagal cadences have different harmonic and outer-voice requirements."),
        _P("Use the Lab as a teacher",
           "Enter only what the assignment gives you and leave unknown cells blank. "
           "Lock required notes, solve for ranked valid alternatives, or enter your own "
           "answer and choose Check. Diagnostics name the exact slots and voices, explain "
           "the rule, and suggest a local repair. A hard error invalidates the answer; "
           "a soft penalty only changes its stylistic ranking."),
    ],
    "form.analysis": [
        _P("Hearing in paragraphs",
           "<b>Form</b> is how phrases build sections and sections build pieces. "
           "The unit is the phrase (usually 4-8 bars, ending in a cadence)."),
        _P("Period vs sentence",
           "A <b>period</b> = antecedent phrase (weak cadence) + consequent "
           "phrase (strong cadence): question-answer. A <b>sentence</b> = idea, "
           "repeated idea, then continuation driving to the cadence (1+1+2)."),
        _P("Binary and ternary",
           "<b>Binary</b> (AB) splits in two halves, often both repeated; "
           "rounded binary brings the opening back after the contrast. "
           "<b>Ternary</b> (ABA) = statement, departure, full return."),
        _P("Sonata form",
           "Sonata form is a giant rounded binary: <b>exposition</b> (two key "
           "areas), <b>development</b> (instability), <b>recapitulation</b> "
           "(both themes home). Track the keys, not just the tunes."),
    ],

    # ================= Pre-Graduate bridge =================
    "posttonal.pitch_classes": [
        _P("Two numbering systems",
           "Tonal <b>scale degrees 1-7</b> depend on a key: C is 1 in C major, "
           "but D is 1 in D major. Post-tonal <b>pitch classes 0-11</b> are fixed "
           "chromatic addresses. Use scale degrees for function in a key and pitch "
           "classes for interval patterns that do not require one."),
        _P("The 0-11 map",
           "C=0, C#/Db=1, D=2, D#/Eb=3, E=4, F=5, F#/Gb=6, G=7, "
           "G#/Ab=8, A=9, A#/Bb=10, B=11. Tables often print <b>T</b> for 10 "
           "and <b>E</b> for 11 so each pitch class occupies one character."),
        _P("Octave and spelling",
           "Pitch class ignores register and normally identifies enharmonic "
           "spellings: C3, C4, and B# can all represent pc 0. That abstraction is "
           "useful, but it does <i>not</i> replace tonal spelling when voice leading "
           "or harmonic function depends on how a note is written."),
        _P("The chromatic clock",
           "A <b>pitch-class clock</b> places 0-11 around a circle in semitone "
           "order. It is not the circle of fifths. Mark a collection such as "
           "C major {0,4,7}; transposing to D major rotates the same shape two "
           "positions to {2,6,9}."),
    ],
    "posttonal.interval_classes": [
        _P("Shortest distance around the clock",
           "An <b>interval class</b> is the shorter distance between two pitch "
           "classes. Because opposite points are six semitones apart, interval "
           "classes run only from 1 through 6."),
        _P("Inversional pairs",
           "IC1 = m2/M7; IC2 = M2/m7; IC3 = m3/M6; IC4 = M3/m6; "
           "IC5 = P4/P5; IC6 = tritone. A perfect fifth spans seven semitones "
           "upward but is IC5 because the opposite direction is five."),
        _P("From pairs to a collection",
           "Calculate the interval class of <i>every unordered pair</i> in a set. "
           "Those tallies become the six entries of an interval-class vector, "
           "an interval-content fingerprint rather than a chord-function label."),
    ],
    "posttonal.normal_form": [
        _P("Pitch classes",
           "Post-tonal theory reduces notes to <b>pitch classes</b> 0-11 (C=0, "
           "C#=1 ... B=11), ignoring octave and spelling. A chord becomes a set "
           "of pcs, e.g. {0, 4, 7} for any C major triad."),
        _P("Normal form",
           "<b>Normal form</b> is the most compact ascending ordering of a pc "
           "set. Try every rotation; pick the one with the smallest span from "
           "first to last (ties: pack smaller intervals to the left)."),
        _P("Worked example",
           "{0, 4, 9}: rotations [0,4,9] span 9, [4,9,0] span 8, [9,0,4] span 7. "
           "Normal form = [9, 0, 4] - an A minor triad's tightest packing."),
    ],
    "posttonal.prime_form": [
        _P("Set classes",
           "Two sets are in the same <b>set class</b> if one maps onto the other "
           "by transposition or inversion. The class's label is its <b>prime "
           "form</b>: normal form transposed to start on 0, compared against its "
           "inversion, taking the more left-packed."),
        _P("Worked example",
           "Major triad [0,4,7] vs its inversion [0,3,7]: the inversion is more "
           "tightly packed left, so the prime form of ALL major and minor triads "
           "is (037). One label for the whole family."),
    ],
    "posttonal.interval_vector": [
        _P("Interval-class content",
           "An <b>interval class</b> reduces every interval to 1-6 (an interval "
           "and its inversion are the same class). The <b>interval-class vector</b> "
           "counts how many of each ic a set contains: six digits, ic1 through ic6."),
        _P("Worked example",
           "Major triad {0,4,7}: pairs are 0-4 (ic4), 0-7 (ic5), 4-7 (ic3) → "
           "vector 001110. The vector predicts how a sonority 'sounds' and what "
           "common tones survive transposition."),
    ],
    "posttonal.forte": [
        _P("Forte's catalogue",
           "Allen Forte numbered every set class: <b>cardinality-ordinal</b>. "
           "3-11 is the major/minor triad family; 4-Z29 is one of the famous "
           "Z-related pairs (same vector, different prime form)."),
        _P("Using the names",
           "Reduce a set to prime form, then look up (or recall) its Forte "
           "number. Landmarks worth memorizing: 3-11 (037) triads, 4-27 (0258) "
           "dominant/half-dim sevenths, 6-35 (02468T) whole-tone."),
    ],
    "posttonal.transforms": [
        _P("Tn: transposition",
           "T<sub>n</sub> adds n to every pitch class, mod 12. T4 of {0,1,5} = "
           "{4,5,9}. Common tones under Tn are predicted by the interval vector "
           "(ic n entry)."),
        _P("TnI: inversion",
           "T<sub>n</sub>I first inverts each pc (12 - pc, mod 12), then adds n. "
           "T0I of {0,1,5} = {0,11,7} = {7,11,0}. Every TnI operation has a "
           "fixed 'index number' n = the sum of each pc and its image."),
    ],
    "posttonal.twelve_tone": [
        _P("The row",
           "A <b>twelve-tone row</b> orders all 12 pitch classes with none "
           "repeated. The row is a theme made of intervals - its character "
           "survives transformation."),
        _P("The four forms",
           "P (prime), I (inversion: intervals flipped), R (retrograde: P "
           "backwards), RI (retrograde inversion). Each comes in 12 transpositions: "
           "48 row forms, all from one idea."),
        _P("The matrix",
           "The 12×12 <b>matrix</b> shows all 48 forms at once: build the first "
           "column as the inversion of the first row, fill rows by transposition. "
           "P reads left→right, I top→bottom, R right→left, RI bottom→top."),
        _P("Numbers become music",
           "A row form supplies <b>pitch-class order</b>, not a finished melody. "
           "After converting numbers back to notes, the composer still chooses "
           "octaves, range, rhythm, meter, articulation, dynamics, texture, "
           "repetition, phrasing, and orchestration."),
    ],
    "posttonal.neo_riemannian": [
        _P("Triads as a network",
           "<b>Neo-Riemannian theory</b> connects triads by smooth voice leading "
           "instead of keys. Three moves, each keeping two common tones: P, L, R."),
        _P("P, L, R",
           "<b>P</b>arallel: C ↔ Cm (3rd moves). <b>L</b>eittonwechsel: C ↔ Em "
           "(root slides down a half step). <b>R</b>elative: C ↔ Am (5th moves up "
           "a whole step). Chains like R-P-L generate famous film-music cycles.",
           play=_chords([[60, 64, 67], [60, 63, 67], [59, 63, 66]], tempo=72)),
        _P("Why composers use it",
           "PLR moves explain chromatic progressions that roman numerals "
           "struggle with (C → Ab → E ...). Hexatonic and octatonic cycles arise "
           "from alternating two moves - the sound of late Romantic mystery."),
        _P("Tonnetz and notation warning",
           "A <b>Tonnetz</b> draws major/minor triads as neighbouring triangles, "
           "making common-tone motion visible. Here P/L/R are chord transforms; "
           "the P, I, R, and RI labels in a twelve-tone matrix belong to a "
           "different system despite sharing letters."),
    ],
    "aural.posttonal_intervals": [
        _P("Hear the complement",
           "Post-tonal interval hearing groups inversional partners together. A "
           "minor 2nd and major 7th both sound maximally close in pitch-class "
           "space and both belong to IC1; a perfect 4th and 5th both belong to IC5.",
           play=_melody(60, 71, 60, 61, tempo=76)),
        _P("A two-pass strategy",
           "First estimate the directed semitone span. If it exceeds six, subtract "
           "it from 12. Then name the interval class. Harmonic presentation is "
           "harder, so sing or arpeggiate the two pitches mentally."),
    ],
    "aural.pc_collections": [
        _P("Cardinality before identity",
           "Before naming a set, hear how many <b>distinct pitch classes</b> it "
           "contains. Register doublings do not add members. Arpeggiate the sound "
           "mentally, count unique attacks, and notice semitone clusters."),
        _P("Connect ear and vector",
           "Dense IC1/IC2 content tends to sound clustered; IC3/IC4 suggests "
           "third-rich sonorities; IC5 emphasizes fourths/fifths; IC6 emphasizes "
           "tritones. The vector names content your ear can learn to recognize."),
    ],
    "aural.neo_riemannian": [
        _P("Two notes stay, one note moves",
           "Hear a P/L/R move by holding the two common tones in your inner ear. "
           "P changes the third, R moves between relative major/minor, and L uses "
           "a leading-tone exchange.",
           play=_chords([[60, 64, 67], [60, 63, 67], [59, 63, 67]], tempo=66)),
        _P("Function is a separate question",
           "Do not force every smooth chromatic triad pair into one key. First "
           "describe the common-tone transformation; then ask whether a convincing "
           "tonal context also supports a Roman-numeral reading."),
    ],
    "piano.pc_collections": [
        _P("Numbers under the fingers",
           "Place 0 at any C, then count every key chromatically to 11 at B. A "
           "pitch-class set accepts any octave, so begin with a compact voicing "
           "and re-space it without changing membership."),
        _P("See the clock on the keyboard",
           "Transpose a collection by moving every key the same number of semitones. "
           "The shape on a pitch-class clock rotates exactly, even when the physical "
           "black/white-key fingering changes."),
    ],
    "piano.row_realization": [
        _P("Order before fingering",
           "A row segment is an ordered list, not a chord. Translate each pc to a "
           "key, preserve the order, and choose octaves that make the line playable."),
        _P("Compose beyond the row",
           "Try the same segment in several registers and rhythms. If the pitch-class "
           "order stays fixed, those changes are legitimate realizations rather "
           "than changes to the row form."),
    ],
    "piano.neo_riemannian": [
        _P("Parsimonious keyboard motion",
           "Play the source triad, hold two common tones, and move only the remaining "
           "voice: P changes the third; R and L connect relative or leading-tone "
           "partners. Use inversions that make that one-note motion visible."),
        _P("Build cycles slowly",
           "Practice single P/L/R moves before chains such as PL, RP, RL, or PLR. "
           "Name each resulting triad and listen for the common tones instead of "
           "memorizing a geometric pattern alone."),
    ],

    # ================= Graduate =================
    "analysis.schenker": [
        _P("Hearing in layers",
           "<b>Schenkerian analysis</b> hears music in structural layers: an "
           "ornamented <i>foreground</i>, simpler <i>middleground</i>, and a deep "
           "<i>background</i> shared by most tonal pieces."),
        _P("The Ursatz",
           "The background <b>Ursatz</b> = a fundamental melodic descent (3-2-1, "
           "or 5-4-3-2-1) over a bass arpeggiation I-V-I. Everything else "
           "elaborates ('prolongs') this skeleton."),
        _P("Prolongation tools",
           "Passing and neighbour tones, arpeggiation, linear progressions "
           "(3rds, 6ths), and voice exchange expand single harmonies across "
           "whole passages. An analysis is an argument about which notes carry "
           "the structure."),
        _P("Reading a graph",
           "Open noteheads = deep structure; stems and slurs group prolongations; "
           "beams trace the Urlinie. Start by graphing short phrases: find the "
           "tonic prolongation, the structural dominant, and the descent."),
    ],
}

LESSONS.update({
    "tonal.modes": [
        _P("A mode has a tonic", "Learn the sound and spelling around a tonal center. D Dorian uses D–E–F–G–A–B–C; D is home. Playing C-major notes from D is a starting construction, not a complete explanation of modal function.",
           play=_melody(62, 64, 65, 67, 69, 71, 72, 74)),
        _P("Compare parallel collections", "Against parallel major: Dorian has flat 3/7, Phrygian flat 2/3/6/7, Lydian sharp 4, Mixolydian flat 7, Aeolian flat 3/6/7, Locrian flat 2/3/5/6/7. Sing the characteristic degree against a tonic drone."),
        _P("Modal versus tonal expectations", "A modal flat 7 is not a leading tone a semitone below tonic. Do not impose V7–I tendencies on every modal phrase. The Part Writing Lab currently uses major/minor tonal context; use these lessons and scale tools for modal study."),
    ],
    "tonal.tendencies": [
        _P("Two different sevenths", "In C major, V7 is G–B–D–F. B is scale degree 7 but the THIRD of the chord. F is scale degree 4 but the SEVENTH of the chord. Keep scale degree and chord factor separate.",
           play=_chord(55, 59, 62, 65), staff={"clef": "treble", "notes": "G4 B4 D5 F5"}),
        _P("Resolve the voices", "In an ordinary V7–I resolution, B rises to C (leading tone → tonic) and F falls to E (chordal seventh → tonic third). In C minor the corresponding resolutions are B→C and F→Eb. Track each voice, not just the collection of destination notes.",
           play=_chords([[55, 59, 62, 65], [48, 60, 60, 64]])),
        _P("Completeness and exceptions", "A complete root-position V7 with strict tendencies may resolve to an incomplete tonic; an incomplete V7 may omit its fifth and double its root. Some courses permit an inner leading tone to fall to scale degree 5. Use the instructor's rule profile. A final V7 can also be a half-cadence ending rather than an unresolved error."),
        _P("Lab checkpoint", "Enter V7–I, put B4 in soprano and F4 in alto in the V7 slot, and solve. Inspect C5 and E4 in those same voices. Then enter F#4 instead of E4 in the tonic slot and read the membership diagnostic."),
    ],
    "tonal.nonchord": [
        _P("Harmony plus rhythmic context", "A note outside the chord is not automatically a mistake. Identify the underlying harmony, metrical position, approach, and departure before naming the event."),
        _P("Passing and neighboring", "Over C major, C–D–E fills a third: D is passing. C–D–C decorates C: D is a neighbor. Both examples use unaccented stepwise dissonance; accented variants need their own context.", play=_melody(60, 62, 64, 60, 62, 60)),
        _P("Suspensions and anticipations", "A suspension is prepared, held into an accented dissonance, then resolves down by step (such as F over a new C bass resolving to E). An anticipation arrives before the harmony to which it belongs. The lab solves chordal snapshots; it does not automatically classify tied or rhythmically accented non-chord tones."),
    ],
    "tonal.phrases": [
        _P("Cadence before label", "Hear and mark phrase endings. A PAC has root-position V–I and tonic in soprano. A half cadence ends on V. A deceptive V–vi avoids the expected tonic; IV–I is plagal."),
        _P("Period and sentence", "A period pairs an antecedent with a more conclusive consequent; parallel periods share opening material. A sentence commonly presents an idea and repetition, then fragmentation/continuation and a cadence. The familiar 2+2+4 pattern is a model, not a universal measure-count law."),
        _P("Assignment checkpoint", "Mark the bass, soprano endpoint, and harmonic rhythm before filling inner voices. I–?–IV alone does not uniquely determine V: key, bass, melodic clues, style and phrase function may permit several answers."),
    ],
    "tonal.tonicization": [
        _P("Read the slash", "V7/V means the dominant seventh of V. In C major it is D–F#–A–C, pointing to G. F# is a temporary leading tone. Resolve the secondary chord's tendencies relative to its target, not blindly to the home tonic.", play=_chords([[50, 57, 60, 66], [43, 55, 59, 67]])),
        _P("Practice in stages", "Identify the target; spell its major dominant triad; add the minor seventh; identify the temporary leading tone; then write the resolution. Try V7/ii, V7/vi, and V7/IV in several major keys."),
        _P("Sequences", "A sequence repeats a pattern at new pitch levels. Applied-dominant chains can keep moving rather than settling immediately. State the assignment's treatment of delayed or transferred tendency resolutions before enforcing a strict local rule."),
    ],
    "tonal.chromatic_predominants": [
        _P("Mixture keeps the tonic", "In C major, iv (F–Ab–C) and bVI (Ab–C–Eb) borrow color from parallel C minor. Compare scale spelling before and after the change; an accidental alone does not establish a new key."),
        _P("Neapolitan sixth", "In C, N6 is Db major in first inversion: F in bass with Db and Ab above. It usually acts as a predominant. Its characteristic lowered scale degree 2 calls for contextual voice-leading, often through cadential six-four."),
        _P("Augmented sixths", "In C, Ab and F# expand outward to G. Italian adds C; French adds C and D; German adds C and Eb. German-to-V can create parallel fifths, which a cadential six-four can help avoid. Spell F#, not Gb, to communicate the rising tendency."),
    ],
    "tonal.modulation": [
        _P("Require tonal evidence", "A secondary dominant briefly tonicizes a chord. A modulation establishes a new tonic through sustained context and cadential support. Analyze the phrase after the chromatic chord, not only the accidental."),
        _P("Pivot in two keys", "C-major vi (A minor) can also be ii in G major. Label the pivot in both keys, then confirm G with its dominant and cadence. Direct and chromatic modulations may avoid a shared diatonic pivot."),
        _P("Before post-tonal study", "Checkpoint: spell modes; resolve V7 in major/minor; complete partial SATB work; distinguish non-chord tones; explain applied chords, mixture, N6/+6; and support phrase/modulation readings with evidence. Then begin pitch classes, sets and neo-Riemannian transformations. Course numbering varies; this is a practice path, not an official Musicianship IV syllabus."),
    ],
})

LESSONS.update({
    "jazz.progressions": [
        _P("A familiar tonal path", "Jazz ii–V–I moves from predominant to dominant to tonic. In C major: Dm7–G7–Cmaj7. Spell the chords before selecting extensions.", play=_chords([[50, 53, 57, 60], [43, 47, 50, 53], [48, 52, 55, 59]])),
        _P("Minor-key choices", "In C minor a common path is Dø7–G7–Cm. Dø7 contains D–F–Ab–C; G7 contains the raised leading tone B. The tonic can use a minor sixth, minor seventh or major seventh according to style. This app's basic minor progression uses Cm7; it is one vocabulary choice."),
        _P("Practice", "Find ii, V and I in several keys. Hear the root motion, then sing thirds and sevenths. The Studio jazz page lets you compare full chords and shell voicings."),
    ],
    "jazz.guides": [
        _P("Third and seventh", "The third and seventh are guide tones: they strongly identify chord quality and suggest voice-leading. Dm7 has F and C; G7 has B and F; Cmaj7 has E and B.", play=_chords([[53, 60], [53, 59], [52, 59]])),
        _P("Shells leave space", "A root-position shell contains root, third and seventh. A bassist can supply the root while a pianist plays guides. An omitted fifth is common; altered fifths may need to be retained to communicate a particular sonority."),
        _P("Connect voices", "Try F–F–E in one voice and C–B–B in another over D–G–C bass. This yields small guide-tone motions. Jazz voicing choices and classical SATB doubling rules serve different textures."),
    ],
    "jazz.substitution": [
        _P("A dominant a tritone away", "In C, Db7 can substitute for G7 before C. This yields Dm7–Db7–Cmaj7 and a descending chromatic bass. It does not mean every dominant is interchangeable in every melody."),
        _P("Shared sound, changed spelling", "G7's guide tones are B and F. Db7's are F and Cb; Cb sounds like B in equal temperament. Their third/seventh roles switch. Keep the spelling appropriate to the written chord.", play=_chords([[43, 47, 53], [37, 47, 53], [36, 47, 52]])),
        _P("Check the melody", "A substitution changes available tensions and can clash with a fixed melodic note. Compare both versions, state the destination tonic, and justify the choice from the actual passage."),
    ],
    "aural.jazz": [
        _P("Follow the bass", "Listen first for the ii–V–I root motion. Then compare ii–bII–I, where the bass descends chromatically. Guide tones alone may be enharmonically shared, so attend to bass context."),
        _P("Hear the same destination", "Compare these two paths in C. Both arrive on tonic; the middle bass changes the route.", play=_chords([[38, 53, 60], [43, 53, 59], [36, 52, 59], [38, 53, 60], [37, 53, 59], [36, 52, 59]])),
        _P("Replay deliberately", "Listen once for bass, once for upper voices, then answer. Replay is unlimited. Repeat the exercise in several keys to avoid identifying only a memorized pitch register."),
    ],
    "piano.jazz": [
        _P("Build a shell", "Find the root, third and seventh of the written chord. Play those pitch classes on the on-screen or MIDI piano; this drill accepts any octave."),
        _P("Then choose a register", "After you can name the tones, place the root low and keep thirds/sevenths near the middle of the keyboard. The Studio example chooses nearby guide tones, but there are multiple valid voicings."),
        _P("Add rhythm yourself", "Move through ii–V–I slowly, then try an even pulse or a short comping rhythm. This pitch-class drill does not grade groove, pedal or physical fingering."),
    ],
})


def lesson_for(skill_id: str) -> list[LessonPage]:
    """Pages for a skill (empty if the skill has no lesson)."""
    return LESSONS.get(skill_id, [])


def has_lesson(skill_id: str) -> bool:
    return bool(LESSONS.get(skill_id))
