"""Isolated SATB rule fixtures, including disputed profile behavior."""

from __future__ import annotations

from music_theory.theory.part_writing.harmony import normalize_constraint
from music_theory.theory.part_writing.models import (
    CadenceType, HarmonyConstraint, HarmonySlot, PartWritingProblem,
    RuleCode, RuleSeverity, Voice, Voicing,
)
from music_theory.theory.part_writing.profiles import (
    CLASSROOM_STRICT, COMMON_PRACTICE, custom_profile,
)
from music_theory.theory.part_writing.rules import (
    validate_cadence, validate_local, validate_parallel_and_direct_intervals,
    validate_melodic_intervals, validate_special_resolution, validate_tendency_tones,
    validate_three_event_melody, validate_voice_overlap,
    validate_voice_order_and_spacing, validate_voice_ranges,
)
from music_theory.theory.pitch import Note


def V(s, a, t, b):
    return Voicing(*(Note.parse(name) for name in (s, a, t, b)))


def problem(*labels, mode="major", cadence=None):
    return PartWritingProblem(mode=mode,
        slots=[HarmonySlot(HarmonyConstraint(roman_numeral=label)) for label in labels],
        cadence=cadence)


def codes(evaluation):
    return {item.code for item in evaluation.violations}


def test_voice_range_crossing_and_spacing():
    assert RuleCode.RANGE in codes(validate_voice_ranges(0, V("A5", "C5", "E4", "C3"),
                                                         COMMON_PRACTICE))
    crossed = validate_voice_order_and_spacing(0, V("C4", "D4", "G3", "C3"), COMMON_PRACTICE)
    assert RuleCode.VOICE_CROSSING in codes(crossed)
    spaced = validate_voice_order_and_spacing(0, V("G5", "C4", "G3", "C3"), COMMON_PRACTICE)
    assert RuleCode.UPPER_SPACING in codes(spaced)


def test_legal_wide_tenor_bass_spacing():
    evaluation = validate_voice_order_and_spacing(0, V("C5", "G4", "C4", "F2"), COMMON_PRACTICE)
    assert RuleCode.UPPER_SPACING not in codes(evaluation)


def test_voice_overlap_detects_both_directions():
    previous = V("C5", "G4", "E4", "C3")
    current = V("E4", "C4", "G3", "E3")
    assert RuleCode.VOICE_OVERLAP in codes(validate_voice_overlap(
        1, previous, current, COMMON_PRACTICE))


def test_parallel_fifths_and_compound_fifths_all_voice_pairs():
    simple = validate_parallel_and_direct_intervals(
        1, V("G4", "C4", "G3", "C3"), V("A4", "D4", "A3", "D3"), COMMON_PRACTICE)
    assert RuleCode.PARALLEL_FIFTH in codes(simple)
    compound = validate_parallel_and_direct_intervals(
        1, V("G4", "E4", "C4", "C3"), V("A4", "F4", "D4", "D3"), COMMON_PRACTICE)
    assert any(item.code == RuleCode.PARALLEL_FIFTH
               and Voice.SOPRANO in item.voices and Voice.BASS in item.voices
               for item in compound.violations)


def test_parallel_octaves_unisons_and_antiparallel_displacement():
    parallels = validate_parallel_and_direct_intervals(
        1, V("C5", "E4", "C4", "C3"), V("D5", "F4", "D4", "D3"), COMMON_PRACTICE)
    assert RuleCode.PARALLEL_OCTAVE in codes(parallels)
    unisons = validate_parallel_and_direct_intervals(
        1, V("C5", "G4", "C4", "C4"), V("D5", "A4", "D4", "D4"), COMMON_PRACTICE)
    assert RuleCode.PARALLEL_UNISON in codes(unisons)
    anti = validate_parallel_and_direct_intervals(
        1, V("C5", "G4", "E4", "C3"), V("C4", "A4", "F4", "C4"), CLASSROOM_STRICT)
    assert RuleCode.ANTIPARALLEL_PERFECT in codes(anti)


def test_parallel_fourths_are_profile_dependent():
    previous = V("C5", "G4", "E4", "C3")
    current = V("D5", "A4", "F4", "D3")
    assert RuleCode.PARALLEL_FOURTH not in codes(
        validate_parallel_and_direct_intervals(1, previous, current, COMMON_PRACTICE))
    assert RuleCode.PARALLEL_FOURTH in codes(
        validate_parallel_and_direct_intervals(1, previous, current, CLASSROOM_STRICT))
    custom = custom_profile()
    custom.severities[RuleCode.PARALLEL_FOURTH] = RuleSeverity.HARD_ERROR
    assert RuleCode.PARALLEL_FOURTH in codes(
        validate_parallel_and_direct_intervals(1, previous, current, custom))


def test_hidden_fifth_requires_outer_similar_motion_and_soprano_leap():
    hidden = validate_parallel_and_direct_intervals(
        1, V("C5", "G4", "E4", "C3"), V("E5", "A4", "E4", "A3"), COMMON_PRACTICE)
    assert RuleCode.HIDDEN_FIFTH in codes(hidden)
    step = validate_parallel_and_direct_intervals(
        1, V("C5", "G4", "E4", "C3"), V("D5", "A4", "F4", "G3"), COMMON_PRACTICE)
    assert RuleCode.HIDDEN_FIFTH not in codes(step)


def test_hidden_octave_is_distinct_from_parallel_octave():
    evaluation = validate_parallel_and_direct_intervals(
        1, V("C5", "G4", "E4", "A2"), V("E5", "A4", "E4", "E3"),
        COMMON_PRACTICE)
    assert RuleCode.HIDDEN_OCTAVE in codes(evaluation)


def test_oblique_and_contrary_motion_are_not_parallel_motion():
    oblique = validate_parallel_and_direct_intervals(
        1, V("G4", "E4", "C4", "C3"), V("A4", "F4", "D4", "C3"), COMMON_PRACTICE)
    contrary = validate_parallel_and_direct_intervals(
        1, V("G4", "E4", "C4", "C3"), V("F4", "D4", "B3", "D3"), COMMON_PRACTICE)
    assert not any(item.code == RuleCode.PARALLEL_FIFTH
                   and set(item.voices) == {Voice.SOPRANO, Voice.BASS}
                   for item in oblique.violations)
    assert not any(item.code == RuleCode.PARALLEL_FIFTH
                   and set(item.voices) == {Voice.SOPRANO, Voice.BASS}
                   for item in contrary.violations)


def test_unequal_fifths_are_configurable():
    previous = V("F#4", "D4", "A3", "C4")
    current = V("G4", "E4", "C4", "C4")
    common = validate_parallel_and_direct_intervals(1, previous, current, COMMON_PRACTICE)
    strict = validate_parallel_and_direct_intervals(1, previous, current, CLASSROOM_STRICT)
    assert any(item.code == RuleCode.UNEQUAL_FIFTH for item in common.violations)
    assert any(item.code == RuleCode.UNEQUAL_FIFTH and item.severity.value == "hard-error"
               for item in strict.violations)


def test_exact_chord_membership_root_and_second_inversion_doubling():
    p = problem("I")
    harmony = normalize_constraint(p.slots[0].harmony, "C", "major")
    wrong = validate_local(0, p, V("C5", "E4", "F3", "C3"), harmony, COMMON_PRACTICE)
    assert RuleCode.CHORD_MEMBERSHIP in codes(wrong)
    p64 = problem("I64")
    h64 = normalize_constraint(p64.slots[0].harmony, "C", "major")
    bad64 = validate_local(0, p64, V("E5", "C5", "C4", "G3"), h64, COMMON_PRACTICE)
    assert RuleCode.REQUIRED_DOUBLING in codes(bad64)


def test_root_position_and_first_inversion_doubling_are_profile_aware():
    root_problem = problem("I")
    root_harmony = normalize_constraint(root_problem.slots[0].harmony, "C", "major")
    root_doubled = validate_local(
        0, root_problem, V("C5", "G4", "E4", "C3"), root_harmony,
        COMMON_PRACTICE)
    assert not root_doubled.hard_violations
    assert "Root doubling" in root_doubled.score_breakdown

    first_problem = problem("I6")
    first_harmony = normalize_constraint(first_problem.slots[0].harmony, "C", "major")
    flexible = validate_local(
        0, first_problem, V("C5", "G4", "C4", "E3"), first_harmony,
        COMMON_PRACTICE)
    assert not flexible.hard_violations


def test_first_inversion_diminished_triad_doubles_its_bass():
    p = problem("viio6")
    harmony = normalize_constraint(p.slots[0].harmony, "C", "major")
    good = validate_local(0, p, V("B4", "F4", "D4", "D3"), harmony,
                          COMMON_PRACTICE)
    bad = validate_local(0, p, V("B4", "F4", "B3", "D3"), harmony,
                         COMMON_PRACTICE)
    assert RuleCode.REQUIRED_DOUBLING not in codes(good)
    assert RuleCode.REQUIRED_DOUBLING in codes(bad)


def test_doubled_leading_tone_and_chordal_seventh():
    p = problem("V7")
    harmony = normalize_constraint(p.slots[0].harmony, "C", "major")
    evaluation = validate_local(0, p, V("B4", "F4", "B3", "G3"), harmony, COMMON_PRACTICE)
    assert RuleCode.DOUBLED_LEADING_TONE in codes(evaluation)
    doubled_seventh = validate_local(0, p, V("F5", "B4", "F4", "G3"), harmony, COMMON_PRACTICE)
    assert RuleCode.DOUBLED_CHORDAL_SEVENTH in codes(doubled_seventh)


def test_leading_tone_and_chordal_seventh_resolution():
    p = problem("V7", "I")
    previous_harmony = normalize_constraint(p.slots[0].harmony, "C", "major")
    good = validate_tendency_tones(
        1, p, V("B4", "F4", "D4", "G3"), V("C5", "E4", "C4", "C3"),
        previous_harmony, COMMON_PRACTICE)
    bad = validate_tendency_tones(
        1, p, V("B4", "F4", "D4", "G3"), V("A4", "G4", "C4", "C3"),
        previous_harmony, COMMON_PRACTICE)
    assert not good.hard_violations
    assert RuleCode.LEADING_TONE_RESOLUTION in codes(bad)
    assert RuleCode.CHORDAL_SEVENTH_RESOLUTION in codes(bad)


def test_applied_leading_tone_resolves_to_its_temporary_tonic():
    p = problem("V/V", "V")
    harmony = normalize_constraint(p.slots[0].harmony, "C", "major")
    good = validate_tendency_tones(
        1, p, V("F#5", "D5", "A4", "D3"), V("G5", "D5", "B4", "G3"),
        harmony, COMMON_PRACTICE)
    bad = validate_tendency_tones(
        1, p, V("F#5", "D5", "A4", "D3"), V("E5", "D5", "B4", "G3"),
        harmony, COMMON_PRACTICE)
    assert RuleCode.LEADING_TONE_RESOLUTION not in codes(good)
    assert RuleCode.LEADING_TONE_RESOLUTION in codes(bad)


def test_augmented_melodic_interval_is_named():
    evaluation = validate_melodic_intervals(
        1, V("C4", "G3", "E3", "C3"), V("F#4", "A3", "F3", "D3"),
        COMMON_PRACTICE)
    assert RuleCode.MELODIC_AUGMENTED in codes(evaluation)


def test_large_leap_recovery_and_consecutive_leaps():
    bad = validate_three_event_melody(
        2, V("C4", "G3", "E3", "C3"), V("G4", "C4", "G3", "G2"),
        V("D5", "F4", "B3", "D3"), CLASSROOM_STRICT)
    assert RuleCode.MELODIC_LEAP_RECOVERY in codes(bad)
    assert RuleCode.CONSECUTIVE_LEAPS in codes(bad)


def test_consecutive_leaps_may_outline_a_triad_but_not_an_arbitrary_set():
    triad = validate_three_event_melody(
        2, V("C4", "G3", "E3", "C3"), V("F4", "C4", "G3", "F2"),
        V("A4", "F4", "C4", "A2"), COMMON_PRACTICE)
    arbitrary = validate_three_event_melody(
        2, V("C4", "G3", "E3", "C3"), V("F4", "C4", "G3", "F2"),
        V("B4", "F#4", "C4", "B2"), COMMON_PRACTICE)
    assert not any(item.code == RuleCode.CONSECUTIVE_LEAPS
                   and item.voices == (Voice.SOPRANO,) for item in triad.violations)
    assert any(item.code == RuleCode.CONSECUTIVE_LEAPS
               and item.voices == (Voice.SOPRANO,) for item in arbitrary.violations)


def test_cadence_types_use_harmony_and_outer_voices():
    p = problem("V", "I", cadence=CadenceType.PERFECT_AUTHENTIC)
    harmonies = [normalize_constraint(slot.harmony, "C", "major") for slot in p.slots]
    good = validate_cadence(p, harmonies,
                            [V("B4", "G4", "D4", "G3"), V("C5", "G4", "E4", "C3")],
                            COMMON_PRACTICE)
    bad = validate_cadence(p, harmonies,
                           [V("D5", "G4", "B3", "G3"), V("E5", "G4", "C4", "C3")],
                           COMMON_PRACTICE)
    assert not good.hard_violations
    assert RuleCode.CADENCE in codes(bad)


def test_half_and_deceptive_cadences_have_independent_contracts():
    half = problem("I", "V", cadence=CadenceType.HALF)
    half_harmonies = [normalize_constraint(slot.harmony, "C", "major")
                      for slot in half.slots]
    half_result = validate_cadence(
        half, half_harmonies,
        [V("E5", "C5", "G4", "C3"), V("D5", "B4", "G4", "G3")],
        COMMON_PRACTICE)
    deceptive = problem("V", "vi", cadence=CadenceType.DECEPTIVE)
    deceptive_harmonies = [normalize_constraint(slot.harmony, "C", "major")
                           for slot in deceptive.slots]
    deceptive_result = validate_cadence(
        deceptive, deceptive_harmonies,
        [V("D5", "G4", "B3", "G3"), V("C5", "A4", "E4", "A3")],
        COMMON_PRACTICE)
    assert not half_result.hard_violations
    assert not deceptive_result.hard_violations


def test_cadential_six_four_suspensions_resolve_down_over_stationary_bass():
    p = problem("I64", "V")
    harmonies = [normalize_constraint(slot.harmony, "C", "major") for slot in p.slots]
    good = validate_special_resolution(
        1, p, V("E5", "C5", "G4", "G3"), V("D5", "B4", "G4", "G3"),
        harmonies[0], harmonies[1], COMMON_PRACTICE)
    bad = validate_special_resolution(
        1, p, V("E5", "C5", "G4", "G3"), V("E5", "C5", "G4", "G3"),
        harmonies[0], harmonies[1], COMMON_PRACTICE)
    assert RuleCode.CADENTIAL_SIX_FOUR not in codes(good)
    assert RuleCode.CADENTIAL_SIX_FOUR in codes(bad)


def test_neapolitan_and_augmented_sixth_have_dedicated_resolution_rules():
    pn = problem("N6", "V", mode="minor")
    hn = [normalize_constraint(slot.harmony, "C", "minor") for slot in pn.slots]
    neapolitan = validate_special_resolution(
        1, pn, V("Db5", "Ab4", "F4", "F3"), V("D5", "G4", "B3", "G3"),
        hn[0], hn[1], COMMON_PRACTICE)
    assert RuleCode.LEADING_TONE_RESOLUTION in codes(neapolitan)
    pa = problem("It+6", "V", mode="minor")
    ha = [normalize_constraint(slot.harmony, "C", "minor") for slot in pa.slots]
    tendency = validate_tendency_tones(
        1, pa, V("F#5", "C5", "C4", "Ab2"), V("F5", "B4", "D4", "G2"),
        ha[0], COMMON_PRACTICE)
    assert RuleCode.AUGMENTED_SIXTH_RESOLUTION in codes(tendency)


def test_fully_diminished_seventh_resolves_leading_tone_and_chordal_seventh():
    p = problem("viio7/V", "V")
    harmony = normalize_constraint(p.slots[0].harmony, "C", "major")
    good = validate_tendency_tones(
        1, p, V("F#5", "Eb5", "C5", "A3"), V("G5", "D5", "B4", "G3"),
        harmony, COMMON_PRACTICE)
    bad = validate_tendency_tones(
        1, p, V("F#5", "Eb5", "C5", "A3"), V("E5", "E5", "B4", "G3"),
        harmony, COMMON_PRACTICE)
    assert not good.hard_violations
    assert RuleCode.LEADING_TONE_RESOLUTION in codes(bad)
    assert RuleCode.CHORDAL_SEVENTH_RESOLUTION in codes(bad)
