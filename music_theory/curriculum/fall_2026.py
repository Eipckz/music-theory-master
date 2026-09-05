"""Offline Fall 2026 course guide derived from the learner's three syllabi.

This is reference and planning data, not application policy.  Course calendars
are explicitly marked tentative because the syllabi allow instructor changes.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Milestone:
    date: str
    title: str
    preparation: tuple[str, ...] = ()


@dataclass(frozen=True)
class CourseUnit:
    title: str
    dates: str
    topics: tuple[str, ...]
    practice: tuple[str, ...] = ()


@dataclass(frozen=True)
class CourseGuide:
    code: str
    title: str
    crn: str
    credits: int
    instructor: str
    contact: str
    meeting: str
    description: str
    prerequisites: str
    materials: tuple[str, ...]
    outcomes: tuple[str, ...]
    assessments: tuple[tuple[str, int], ...]
    policies: tuple[str, ...]
    technology: tuple[str, ...]
    grading_notes: tuple[str, ...]
    units: tuple[CourseUnit, ...]
    milestones: tuple[Milestone, ...]


MUS_2710 = CourseGuide(
    code="MUS 2710", title="Musicianship III", crn="44068", credits=2,
    instructor="Dr. Sean Fredenburg",
    contact="Sean-Fredenburg@utc.edu · FAC 108, by appointment",
    meeting="Monday/Wednesday/Friday 9:10-10:05 a.m., FAC 218",
    description=(
        "Standard non-diatonic harmony, aural and visual analysis and notation, "
        "melodic composition and harmonization, and standard musical forms."
    ),
    prerequisites=(
        "MUS 1720 or equivalent with C or better; co-requisite MUS 2730, and "
        "MUS 2750 for Bachelor of Music majors."
    ),
    materials=(
        "Musition Cloud subscription", "MUS 2710 course packet",
        "Three-ring binder", "Music manuscript paper and pencil", "Notebook",
    ),
    outcomes=(
        "Analyze and use all diatonic triads and seventh chords.",
        "Create, recognize, and use applied dominants and mixture/borrowed chords.",
        "Realize chord progressions in four-part SATB texture with competent voice leading.",
        "Recognize and use embellishing tones, motives, subphrases, phrases, phrase units, and cadences.",
        "Analyze folk, popular, art-song, ternary, compound ternary, and rondo forms.",
        "Locate pivot-chord, sequential, and phrase modulations and explain harmonic rhythm.",
        "Transpose treble-clef B-flat instruments and F instruments to concert pitch.",
        "Discuss expressive purposes of harmony, melody, and text interaction.",
    ),
    assessments=(("Assignments", 45), ("Three unit exams", 30),
                 ("Comprehensive final", 15), ("Participation/discussion", 10)),
    policies=(
        "Attendance and active participation are expected; two unexcused absences are allowed before the grade may be affected.",
        "Ordinary late work is accepted up to two class days late; serious illness or emergency extensions require timely contact.",
        "Calendar dates are tentative; use Canvas for the current assignment details.",
        "Bring the course packet each class day. Phones are for documented board photos or urgent, pre-arranged communication only.",
        "Civil, respectful participation and questions are expected; submitted work follows the UTC Honor Code.",
    ),
    technology=(
        "Internet-connected computer, speakers/headphones, Canvas, and Musition Cloud",
        "Ability to save PDFs and prepare readable Word, Google Docs, or legible paper submissions",
        "Music Division computer lab and UTC Library Studio offer computers, printing, recording gear, and assistance",
    ),
    grading_notes=(
        "90-100 A; 80-89 B; 70-79 C; 60-69 D; below 60 F",
        "Bachelor of Music majors need C or better to continue; D/F requires retaking the course.",
        "No curve or extra credit. Values above x.50 round upward; feedback is normally returned in about one week.",
    ),
    units=(
        CourseUnit("Unit 1", "Aug 24-Sep 20", (
            "Diatonic triads/sevenths, cadences, meter, counting, and beaming review",
            "V/V and V7/V in major and minor", "Folk and popular song forms",
            "Sus4 and typical popular harmony", "Diatonic modes",
            "Melodic construction, melody-harmony interaction, and harmonic rhythm",
        ), ("Create and resolve V/V and V7/V", "Analyze phrase and popular-song form")),
        CourseUnit("Unit 2", "Sep 21-Oct 18", (
            "V7/IV and the applied dominant of iv in minor",
            "Applied dominants V/ii, V/iii, V/vi; V7/III, V7/VI, V7/VII in minor",
            "Strophic, through-composed, modified strophic, and aria forms",
            "Pivot-chord and phrase modulation", "Embellishing tones",
            "B-flat instrument transposition", "Concert-music harmonic rhythm",
        ), ("SATB applied-dominant realizations", "B-flat transposition drills")),
        CourseUnit("Unit 3", "Oct 19-Nov 8", (
            "Ternary and compound ternary form", "Mixture/borrowed chords",
            "Sequential modulation", "F-instrument transposition",
            "Expressive uses of mode mixture",
        ), ("Compare diatonic and borrowed harmonizations", "F transposition drills")),
        CourseUnit("Unit 4", "Nov 9-Dec 2", (
            "Rondo form", "Comparison and review of applied dominants and borrowed chords",
            "B-flat and F transposition review", "Cumulative review of forms and song types",
        ), ("Mixed chromatic-harmony SATB practice", "Cumulative form analysis")),
    ),
    milestones=(
        Milestone("2026-09-18", "Unit 1 exam window", ("Diatonic harmony", "V/V and V7/V", "Folk/pop form")),
        Milestone("2026-10-16", "Unit 2 exam window", ("Applied dominants", "Art song", "Modulation", "B-flat transposition")),
        Milestone("2026-11-06", "Unit 3 exam window", ("Ternary form", "Borrowed chords", "F transposition")),
        Milestone("2026-12-02", "Final exam, 8-10 a.m.", ("Units 1-4 cumulative review",)),
    ),
)


MUS_2750 = CourseGuide(
    code="MUS 2750", title="Aural Skills III", crn="44070", credits=2,
    instructor="Dr. Sean Fredenburg",
    contact="Sean-Fredenburg@utc.edu · FAC 108, by appointment",
    meeting="Monday/Wednesday 11:30 a.m.-12:25 p.m., FAC 218",
    description=(
        "Advanced rhythm, sight singing, aural recognition and dictation of "
        "diatonic/non-diatonic melody, harmony, cadence, form, and improvisation."
    ),
    prerequisites="MUS 1760 with C or better; co-requisites MUS 2710 and MUS 2730.",
    materials=(
        "Folk Song Sight-Singing Series Books V and IX", "Staff paper and pencil",
        "Auralia desktop subscription", "Speakers or headphones",
    ),
    outcomes=(
        "Detect and correct errors in rhythm, melody, chords, and progressions.",
        "Identify every interval through the octave and complex rhythms in simple/compound meter.",
        "Identify major, three minor forms, Mixolydian, Dorian, Lydian, Phrygian, and Locrian.",
        "Identify major/minor/modal tonality and perfect/imperfect authentic, half, plagal, and deceptive cadences.",
        "Recognize triads and dominant/diminished sevenths in the required positions and inversions.",
        "Hear diatonic progressions, six-four functions, secondary dominants, and borrowed bVII/iv.",
        "Recognize repeated/parallel/contrasting phrases, sentences, binary, rounded binary, and ternary forms.",
        "Dictate pitch, rhythm, melody, and a soprano or bass line from four-part texture.",
        "Sight-sing diatonic/chromatic melody and sing four-part progressions on solfege.",
        "Repeat tonal/rhythmic material and improvise rhythms, chord patterns, and melodies over harmony.",
    ),
    assessments=(("Daily class work", 25), ("Auralia/Sight Reading Factory assignments", 22),
                 ("Pop progression quizzes", 3), ("Unit tests", 15),
                 ("Singing exams", 15), ("Final exams", 20)),
    policies=(
        "Work is due at the beginning of the listed class; each 24-hour late period reduces credit by 10%, up to 50%.",
        "Punctual attendance and full drill participation are part of the daily-class-work grade.",
        "The calendar is tentative; verify current details in Canvas and Auralia.",
        "A tardy student's daily grade cannot exceed 80%; excused absences require documentation.",
        "Aural Skills is an active lab: drills, partner work, singing, dictation, and improvisation require full participation.",
    ),
    technology=(
        "Computer with reliable internet, Canvas, UTC email, and the Auralia desktop app",
        "Speakers or headphones for audio; check Canvas and UTC email regularly",
        "16 Auralia assignments (four per unit) and six Sight Reading Factory assignments (two in Units 2-4)",
    ),
    grading_notes=(
        "90-100 A; 80-89 B; 70-79 C; 60-69 D; 59 or below F",
        "Auralia feedback is immediate; other grading is returned within seven days at most.",
        "Three written unit tests; Singing Exams 1 and 3 are video uploads, Exam 2 and the final are in person.",
        "The cumulative finals include an in-class pop quiz, Auralia/Canvas work, and an appointment singing exam.",
    ),
    units=(
        CourseUnit("Unit 1", "Aug 24-Sep 14", (
            "m2, M2, m3, M3, P4, tritone, P5, P8",
            "Major and all minor scales/tonalities", "Major, minor, and dominant seventh block chords",
            "Authentic versus half cadence", "Repeated, parallel, and contrasting phrases",
            "Major I, ii, IV, V7, vi; minor i, iv, V7, VI",
            "I-IV-V, I-V-IV, major vamp I-V-IV-V, and I-IV-V-IV",
        ), ("Interval pivot-note singing", "Basic dictation/error detection", "Primary-chord improvisation")),
        CourseUnit("Unit 2", "Sep 14-Oct 12", (
            "m6, M6, m7, M7", "Mixolydian and Dorian",
            "Arpeggiated triads and V7 in all inversions", "Authentic versus plagal cadence",
            "Sentences", "iii, first-inversion triads, and functional six-four chords",
            "ii-V-I jazz turnaround, Mixolydian I-bVII-IV-I, Aeolian i-bVII, Dorian i-IV",
        ), ("Inversion recognition", "6/4 classification", "Modal-vamp improvisation")),
        CourseUnit("Unit 3", "Oct 12-Nov 9", (
            "Lydian, Phrygian, and Locrian", "Diminished triads and diminished sevenths",
            "Perfect versus imperfect authentic cadence", "Simple and rounded binary",
            "V/V and V7/V; V/iv and V7/IV", "Axis I-V-vi-IV and its minor/plagal variations",
        ), ("Secondary-dominant dictation", "Cadence-soprano diagnosis", "Axis improvisation")),
        CourseUnit("Unit 4", "Nov 9-Dec 4", (
            "Cumulative intervals, modes, tonalities, chords, and cadences",
            "Authentic versus deceptive cadence", "Ternary form",
            "Borrowed bVII and iv in major", "Phrygian dominant and double harmonic scales",
            "I-IV-vi-V, I-vi-IV-V, and IV-V-I-vi pop progressions",
        ), ("Borrowed-chord error detection", "Deceptive cadence dictation", "Cumulative sight singing")),
    ),
    milestones=(
        Milestone("2026-09-14", "Unit 1 test and Singing Exam 1 due", ("Harmonic minor", "Intervals through P4", "Folk-song solfege")),
        Milestone("2026-10-01", "Singing Exam 2 appointment window begins", ("Tonal memory", "Sight singing", "Improvisation")),
        Milestone("2026-10-12", "Unit 2 test due", ("Sixths/sevenths", "Modes", "Inversions", "Plagal cadence")),
        Milestone("2026-11-02", "Singing Exam 3 due", ("Five church modes", "P5-P8", "Folk-song solfege")),
        Milestone("2026-11-09", "Unit 3 test due", ("Applied dominants", "Binary form", "PAC versus IAC")),
        Milestone("2026-11-30", "Pop progression final", ("All unit progressions",)),
        Milestone("2026-12-04", "Auralia/written final due by 11:59 p.m.", ("Cumulative Units 1-4",)),
    ),
)


MUS_2730 = CourseGuide(
    code="MUS 2730", title="Musicianship Lab III", crn="44069", credits=1,
    instructor="Dr. Danny Milan",
    contact="daniel-milan@utc.edu · Cadek 305, by appointment",
    meeting="Tuesday/Thursday 9:40-10:35 a.m., Keyboard Lab",
    description="Keyboard and written-drill application of concurrent Musicianship III skills.",
    prerequisites=(
        "Acceptable Musicianship Prep Proficiency result or department approval; "
        "co-requisites Musicianship III and Aural Skills III."
    ),
    materials=("Alfred's Group Piano for Adults, Book 2", "Speakers/headphones", "Video-recording access"),
    outcomes=(
        "Apply concurrent theory concepts at the keyboard and dry-erase board.",
        "Play all major and harmonic-minor scales hands separately for two octaves.",
        "Balance one hand over another and coordinate legato with non-legato articulation.",
        "Sight-read and transpose right-hand melodies within an octave over left-hand inverted chords.",
        "Use damper pedal appropriately in repertoire, accompaniments, and exercises.",
        "Lead vocal warm-ups while playing major pentascales with I-V6/5-I and descending whole-tone patterns.",
        "Accompany a vocalist from standard teaching repertoire.",
        "Realize lead sheets from popular chord symbols.",
        "Transpose B-flat and F instrumental parts to concert pitch at the keyboard.",
        "Harmonize and transpose melodies using dominant seventh chords.",
        "Read progressively difficult grand-staff notation and transpose sight reading by whole step.",
        "Perform a prepared three-part SATB open score with suitable fingering, hand distribution, and pedal.",
        "Perform early-intermediate repertoire stylistically and critique performances objectively.",
    ),
    assessments=(("Five-week exam", 15), ("Ten-week exam", 15),
                 ("Final exam", 25), ("Assignments", 30),
                 ("Participation", 15)),
    policies=(
        "Attendance and active keyboard/ensemble participation are required and form 15% of the grade.",
        "Assignments are performance checkpoints; documented emergency makeups are normally completed within one week.",
        "Grading considers note/rhythm accuracy, tempo, fingering, continuity, musicality, and pedal use.",
        "Each class day is a 100-point attendance/engagement assignment; partial attendance earns proportional credit.",
        "School trips, government duty, religious holidays, and documented illness do not count against allowable absences when communicated appropriately.",
        "Late exams require an emergency and notice 24 hours beforehand; approved makeup work is normally completed within one week.",
    ),
    technology=(
        "Reliable internet, Canvas, speakers/headphones, an updated PDF reader, and regular video recording/submission",
        "Video may be submitted through an unlisted YouTube link or UTC OneDrive as directed in Canvas",
        "Music Division lab and UTC Library Studio provide computers, Finale, printing, and audio/video equipment",
    ),
    grading_notes=(
        "90-100 A; 80-89 B; 70-79 C; 60-69 D; 0-59 F; grades round to the nearest whole number.",
        "Email response is generally within 48 hours and grading feedback within one week.",
        "Exams evaluate note/rhythm accuracy, tempo, fingering, continuity, musicality, and damper pedal use.",
    ),
    units=(
        CourseUnit("Technique and scales", "All semester", (
            "Major and harmonic-minor scales", "Hand balance", "Legato/non-legato coordination", "Damper pedal",
        ), ("Two-octave scale rotation", "Hands-alone articulation drills")),
        CourseUnit("Harmony at the keyboard", "All semester", (
            "Inverted left-hand chords", "I-V6/5-I pentascale warm-ups",
            "Dominant-seventh harmonization", "Popular chord-symbol lead sheets",
        ), ("Transpose a harmonization", "Lead-sheet realization", "V7 resolution in every key")),
        CourseUnit("Reading, transposition, and ensemble", "All semester", (
            "Grand-staff reading", "Whole-step sight-reading transposition",
            "Concert-pitch transposition", "Three-part SATB open score", "Vocal accompaniment",
        ), ("One-octave melody transposition", "Open-score reduction", "Record and self-critique")),
    ),
    milestones=(
        Milestone("2026-09-28", "Approximate five-week exam checkpoint", ("Technique", "Scales", "Reading", "Harmony")),
        Milestone("2026-11-02", "Approximate ten-week exam checkpoint", ("Transposition", "V7 harmonization", "Lead sheet")),
        Milestone("2026-12-04", "Final-exam preparation window", ("Cumulative performance goals",)),
    ),
)


FALL_2026_COURSES = (MUS_2710, MUS_2750, MUS_2730)

UTC_SUPPORT = (
    "IT Help Desk: 423-425-4000 · helpdesk@utc.edu",
    "Disability Resource Center: 423-425-4006 · DRC@utc.edu",
    "Counseling Center appointments: 423-425-4438 · crisis support: 423-425-CARE (2273) or 911",
    "Student Outreach & Support / Scrappy's Cupboard / emergency-fund help: 423-425-2299",
    "Records Office (late-withdrawal questions): 423-425-4416",
    "UTC-ALERT carries emergency and closure instructions. Follow the current alert and course communication.",
    "AI use is assignment-specific under UTC policy: follow the instructor's stated permission level and the Honor Code; acknowledge protected sources when required.",
)


def course_by_code(code: str) -> CourseGuide | None:
    return next((course for course in FALL_2026_COURSES if course.code == code), None)
