"""Part-writing data-model, profile, and harmony-normalization contracts."""

from __future__ import annotations

from music_theory.theory.part_writing.harmony import (
    chord_symbol_to_chord, functional_candidates, harmonies_for_slot,
    normalize_constraint,
)
from music_theory.theory.part_writing.models import (
    CadenceType, ChordFactor, HarmonyConstraint, HarmonySlot,
    PartWritingProblem, Voice, Voicing,
)
from music_theory.theory.part_writing.profiles import (
    CLASSROOM_STRICT, COMMON_PRACTICE, custom_profile,
)
from music_theory.theory.pitch import Note


def test_voicing_preserves_voice_identity_and_spelling():
    voicing = Voicing(Note.parse("Db5"), Note.parse("Ab4"),
                      Note.parse("F4"), Note.parse("Db3"))
    assert voicing[Voice.SOPRANO].name == "Db5"
    assert voicing.spelled_tuple == ("Db5", "Ab4", "F4", "Db3")
    assert voicing.midi_tuple[0] == 73


def test_common_and_strict_profiles_disagree_about_parallel_fourths():
    from music_theory.theory.part_writing.models import RuleCode, RuleSeverity
    assert COMMON_PRACTICE.severity(RuleCode.PARALLEL_FOURTH) == RuleSeverity.DISABLED
    assert CLASSROOM_STRICT.severity(RuleCode.PARALLEL_FOURTH) == RuleSeverity.HARD_ERROR


def test_custom_profile_is_an_independent_copy():
    from music_theory.theory.part_writing.models import RuleCode, RuleSeverity
    custom = custom_profile()
    custom.severities[RuleCode.PARALLEL_FOURTH] = RuleSeverity.HARD_ERROR
    assert COMMON_PRACTICE.severity(RuleCode.PARALLEL_FOURTH) == RuleSeverity.DISABLED


def test_roman_normalization_preserves_spelling_and_inversion():
    harmony = normalize_constraint(HarmonyConstraint(roman_numeral="V65"), "Bb", "major")
    assert [note.name_no_octave for note in harmony.members] == ["F", "A", "C", "Eb"]
    assert harmony.inversion == 1
    assert harmony.bass_factor == ChordFactor.THIRD


def test_chord_symbol_and_slash_bass():
    chord = chord_symbol_to_chord("G7/B")
    assert chord.quality == "dom7" and chord.inversion == 1
    assert [note.name_no_octave for note in chord.members] == ["G", "B", "D", "F"]


def test_two_harmony_labels_must_agree():
    constraint = HarmonyConstraint(roman_numeral="V", chord_symbol="F")
    try:
        normalize_constraint(constraint, "C", "major")
    except ValueError as exc:
        assert "different harmonies" in str(exc)
    else:  # pragma: no cover - explicit failure message
        raise AssertionError("conflicting labels were accepted")


def test_special_chromatic_spellings_are_explicit():
    n6 = normalize_constraint(HarmonyConstraint(roman_numeral="N6"), "C", "minor")
    german = normalize_constraint(HarmonyConstraint(roman_numeral="Ger+6"), "C", "minor")
    assert [note.name_no_octave for note in n6.members] == ["Db", "F", "Ab"]
    assert n6.inversion == 1 and n6.special == "neapolitan"
    assert [note.name_no_octave for note in german.members] == ["Ab", "C", "Eb", "F#"]
    assert german.special == "augmented-sixth"


def test_blank_harmony_uses_grammar_but_does_not_override_explicit_input():
    problem = PartWritingProblem(slots=[HarmonySlot(), HarmonySlot(), HarmonySlot()],
                                 cadence=CadenceType.HALF)
    assert {"I", "ii6", "IV", "V7"} <= set(functional_candidates(problem, 0))
    assert functional_candidates(problem, 2) == ["V"]


def test_allowed_and_forbidden_harmony_constraints_filter_blank_grammar():
    constraint = HarmonyConstraint(
        allowed_harmonies=("I", "vi"), forbidden_harmonies=("vi",))
    problem = PartWritingProblem(slots=[HarmonySlot(constraint)])
    assert [harmony.label for harmony in harmonies_for_slot(problem, 0)] == ["I"]
