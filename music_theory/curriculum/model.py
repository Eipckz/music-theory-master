"""Skill-tree model and the concrete curriculum definition."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..adaptive.mastery import difficulty_for_rating, rating_for_difficulty

LEVEL_ORDER = ["Beginner", "Early", "Intermediate", "Advanced", "Graduate"]
_MASTERY_THRESHOLD = 0.72   # P(known) at which a skill counts as a satisfied prereq


@dataclass(frozen=True)
class Skill:
    id: str
    title: str
    domain: str                       # theory | aural | piano
    level: str                        # one of LEVEL_ORDER
    etypes: tuple[str, ...] = ()      # generators training this skill
    prereqs: tuple[str, ...] = ()
    diff_range: tuple[float, float] = (0.0, 10.0)
    guided: bool = False              # informational/self-assessed (no auto-drill)
    description: str = ""

    @property
    def schedulable(self) -> bool:
        return bool(self.etypes) and not self.guided


class Curriculum:
    def __init__(self, skills: list[Skill]) -> None:
        self.skills: dict[str, Skill] = {s.id: s for s in skills}
        self._order = [s.id for s in skills]

    def __iter__(self):
        return iter(self.skills[i] for i in self._order)

    def get(self, skill_id: str) -> Optional[Skill]:
        return self.skills.get(skill_id)

    def by_domain(self, domain: str) -> list[Skill]:
        return [self.skills[i] for i in self._order if self.skills[i].domain == domain]

    def by_level(self, level: str) -> list[Skill]:
        return [self.skills[i] for i in self._order if self.skills[i].level == level]

    # -- prerequisite / unlock logic -------------------------------------
    def is_mastered(self, db, skill_id: str) -> bool:
        m = db.get_mastery(skill_id)
        return bool(m and m.get("mastery_prob", 0) >= _MASTERY_THRESHOLD and m.get("n_attempts", 0) >= 3)

    def prereqs_met(self, db, skill_id: str) -> bool:
        skill = self.skills.get(skill_id)
        if not skill:
            return False
        return all(self.is_mastered(db, p) for p in skill.prereqs)

    def is_unlocked(self, db, skill_id: str) -> bool:
        m = db.get_mastery(skill_id)
        if m and m.get("unlocked"):
            return True
        return self.prereqs_met(db, skill_id)

    def unlocked_skills(self, db) -> list[Skill]:
        return [s for s in self if s.schedulable and self.is_unlocked(db, s.id)]

    def newly_available(self, db) -> list[Skill]:
        """Schedulable skills whose prereqs are now met but aren't unlocked yet."""
        out = []
        for s in self:
            if not s.schedulable:
                continue
            m = db.get_mastery(s.id)
            already = bool(m and m.get("unlocked"))
            if not already and self.prereqs_met(db, s.id):
                out.append(s)
        return out

    # -- placement seeding ------------------------------------------------
    def seed_from_placement(self, db, domain: str, theta: float) -> None:
        """Unlock skills in a domain up to the placed level and seed ratings."""
        rating = rating_for_difficulty(theta)
        for s in self.by_domain(domain):
            if not s.schedulable:
                continue
            lo, hi = s.diff_range
            cur = db.get_mastery(s.id) or {}
            if lo <= theta:
                prob = 0.62 if hi <= theta else 0.35
                seed_rating = min(rating, rating_for_difficulty(hi))
                # A retake must never erase real progress: keep the better of
                # the existing and the seeded estimates.
                db.upsert_mastery(
                    s.id,
                    rating=max(float(cur.get("rating", 0.0)), seed_rating),
                    mastery_prob=max(float(cur.get("mastery_prob", 0.0)), prob),
                    unlocked=1,
                    n_attempts=max(int(cur.get("n_attempts", 0)), 3),
                    n_correct=int(cur.get("n_correct", 0)),
                )
            elif not cur:
                db.upsert_mastery(s.id, unlocked=0)


def _S(*args, **kwargs) -> Skill:
    return Skill(*args, **kwargs)


# ---------------------------------------------------------------------------
# The skill tree (beginner -> PhD). Each schedulable skill maps to generators.
# ---------------------------------------------------------------------------
_SKILLS: list[Skill] = [
    # ---- Beginner ----
    _S("fund.note_names", "Note Names & the Staff", "theory", "Beginner",
       ("note_identification",), (), (0.0, 3.0),
       description="Read note names on treble and bass clefs."),
    _S("aural.intervals", "Hearing Intervals", "aural", "Beginner",
       ("interval_recognition",), (), (0.0, 4.0),
       description="Recognize intervals by ear."),
    _S("aural.melodic_dictation", "Melodic Dictation", "aural", "Beginner",
       ("melodic_dictation",), (), (0.0, 9.0),
       description="Notate melodies you hear - from two notes to long phrases."),
    _S("piano.find_notes", "Keyboard Geography", "piano", "Beginner",
       ("play_note",), (), (0.0, 3.0),
       description="Locate notes on the keyboard."),
    _S("aural.rhythmic_dictation", "Rhythmic Dictation", "aural", "Beginner",
       ("rhythmic_dictation",), (), (0.0, 6.0),
       description="Reproduce rhythms you hear."),

    # ---- Early ----
    _S("fund.intervals", "Intervals (Written)", "theory", "Early",
       ("interval_identification", "interval_construction"), ("fund.note_names",), (1.0, 6.0),
       description="Identify and build intervals by number and quality."),
    _S("scales.key_signatures", "Key Signatures", "theory", "Early",
       ("key_signature_identification",), ("fund.note_names",), (1.0, 7.0),
       description="Major/minor key signatures and the circle of fifths."),
    _S("scales.spell", "Scale Spelling", "theory", "Early",
       ("scale_spelling",), ("fund.note_names",), (1.0, 6.0),
       description="Spell major and minor scales."),
    _S("scales.identify", "Scale Identification", "theory", "Early",
       ("scale_identification",), ("scales.spell",), (2.0, 8.0),
       description="Identify scale and mode types."),
    _S("chords.triad_quality", "Triad Quality", "theory", "Early",
       ("triad_quality",), ("fund.intervals",), (1.0, 5.0),
       description="Major, minor, diminished, augmented triads."),
    _S("chords.triad_spell", "Triad Spelling", "theory", "Early",
       ("triad_spelling",), ("chords.triad_quality",), (1.0, 6.0),
       description="Spell triads of any quality."),
    _S("piano.intervals", "Play Intervals", "piano", "Early",
       ("play_interval",), ("piano.find_notes",), (1.0, 6.0)),
    _S("piano.scales", "Play Scales", "piano", "Early",
       ("play_scale",), ("piano.find_notes",), (1.0, 7.0)),
    _S("aural.chord_quality", "Chord Quality (Ear)", "aural", "Early",
       ("chord_quality_ear",), ("aural.intervals",), (1.0, 7.0)),
    _S("aural.scales", "Scales & Modes (Ear)", "aural", "Early",
       ("scale_mode_ear",), ("aural.intervals",), (2.0, 9.0)),

    # ---- Intermediate ----
    _S("chords.seventh_quality", "Seventh-Chord Quality", "theory", "Intermediate",
       ("seventh_quality",), ("chords.triad_quality",), (3.0, 8.0)),
    _S("chords.inversions", "Inversions & Figured Bass", "theory", "Intermediate",
       ("chord_inversion",), ("chords.triad_spell",), (3.0, 8.0)),
    _S("harmony.roman_numerals", "Roman-Numeral Analysis", "theory", "Intermediate",
       ("roman_numeral_analysis",), ("chords.triad_quality", "scales.key_signatures"), (3.0, 9.0)),
    _S("harmony.roman_build", "Build From Roman Numerals", "theory", "Intermediate",
       ("roman_numeral_build",), ("harmony.roman_numerals",), (3.0, 9.0)),
    _S("piano.chords", "Play Chords", "piano", "Intermediate",
       ("play_triad",), ("piano.intervals",), (2.0, 7.0)),
    _S("aural.cadences", "Cadence Identification", "aural", "Intermediate",
       ("cadence_ear",), ("aural.chord_quality",), (2.0, 7.0)),
    _S("aural.error_detection", "Error Detection", "aural", "Intermediate",
       ("error_detection",), ("aural.melodic_dictation",), (3.0, 9.0)),
    _S("counterpoint.species", "Species Counterpoint", "theory", "Intermediate",
       (), ("harmony.roman_numerals",), (4.0, 9.0), guided=True,
       description="First through fifth species (guided lessons + self-check)."),

    # ---- Advanced ----
    _S("aural.harmonic_dictation", "Harmonic Dictation", "aural", "Advanced",
       ("harmonic_dictation",), ("aural.cadences", "harmony.roman_numerals"), (3.0, 9.0)),
    _S("aural.multipart", "Multi-Part Dictation", "aural", "Advanced",
       ("multipart_dictation",), ("aural.melodic_dictation", "aural.harmonic_dictation"), (3.0, 10.0),
       description="Transcribe two, three, then four simultaneous voices - "
                   "the bridge from single-line hearing to full-texture hearing."),
    _S("harmony.chromatic", "Chromatic Harmony", "theory", "Advanced",
       ("roman_numeral_analysis",), ("harmony.roman_build", "chords.seventh_quality"), (6.0, 9.5),
       description="Secondary function, mixture, Neapolitan, augmented sixths."),
    _S("form.analysis", "Form & Phrase Structure", "theory", "Advanced",
       (), ("harmony.roman_numerals",), (5.0, 9.0), guided=True,
       description="Periods, sentences, binary/ternary, sonata (guided)."),

    # ---- Graduate / PhD ----
    _S("posttonal.normal_form", "PC Sets: Normal Form", "theory", "Graduate",
       ("pcset_normal_form",), ("fund.intervals",), (4.0, 8.0)),
    _S("posttonal.prime_form", "PC Sets: Prime Form", "theory", "Graduate",
       ("pcset_prime_form",), ("posttonal.normal_form",), (5.0, 9.0)),
    _S("posttonal.interval_vector", "Interval-Class Vector", "theory", "Graduate",
       ("pcset_interval_vector",), ("posttonal.normal_form",), (5.0, 9.0)),
    _S("posttonal.forte", "Forte Set Classes", "theory", "Graduate",
       ("forte_identification",), ("posttonal.prime_form",), (6.0, 10.0)),
    _S("posttonal.transforms", "Tn / TnI Operations", "theory", "Graduate",
       ("set_transposition",), ("posttonal.normal_form",), (5.0, 9.5)),
    _S("posttonal.twelve_tone", "Twelve-Tone Technique", "theory", "Graduate",
       ("row_form_identification", "row_matrix_lookup"), ("posttonal.transforms",), (6.0, 10.0)),
    _S("posttonal.neo_riemannian", "Neo-Riemannian Theory", "theory", "Graduate",
       ("neo_riemannian",), ("harmony.chromatic",), (6.0, 10.0)),
    _S("analysis.schenker", "Schenkerian Analysis", "theory", "Graduate",
       (), ("form.analysis",), (7.0, 10.0), guided=True,
       description="Foreground/middleground reduction and the Ursatz (guided)."),
]

CURRICULUM = Curriculum(_SKILLS)
