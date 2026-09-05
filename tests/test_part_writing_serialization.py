"""Versioned JSON preserves every user constraint without unsafe formats."""

from __future__ import annotations

import json

import pytest

from music_theory.theory.part_writing.models import (
    CadenceType, ChordFactor, Clef, HarmonyConstraint, HarmonySlot, Layout,
    PartWritingProblem, PitchConstraint, RuleCode, RuleSeverity, Voice,
)
from music_theory.theory.part_writing.profiles import custom_profile
from music_theory.theory.part_writing.serialization import (
    SerializationError, dumps_problem, load_problem, loads_problem,
    problem_from_dict, problem_to_dict, profile_from_dict, profile_to_dict,
    save_problem,
)
from music_theory.theory.pitch import Note


def rich_problem():
    slot = HarmonySlot(HarmonyConstraint(
        roman_numeral="V65/V", figured_bass="65", inversion=1,
        exact_bass_pitch=Note.parse("F#3"),
        required_chord_tones=("third", "seventh"),
        forbidden_chord_tones=("C",), required_doubling=ChordFactor.ROOT,
        allowed_harmonies=("V65/V",), forbidden_harmonies=("Ger+6",),
    ), duration=2.0, cadence_role="predominant", label="Applied dominant")
    slot.voice(Voice.SOPRANO).pitch = PitchConstraint(
        pitch_class=Note.parse("A"), minimum=Note.parse("C4"),
        maximum=Note.parse("G5"))
    slot.voice(Voice.SOPRANO).locked = True
    slot.voice(Voice.SOPRANO).clef = Clef.TREBLE
    slot.voice(Voice.SOPRANO).source_label = "given melody"
    slot.voice(Voice.ALTO).pitch = PitchConstraint(scale_degree=2)
    slot.voice(Voice.TENOR).pitch = PitchConstraint(chord_factor=ChordFactor.SEVENTH)
    slot.voice(Voice.BASS).pitch = PitchConstraint(exact=Note.parse("F#3"))
    return PartWritingProblem(
        key_tonic="G", mode="major", meter=(3, 4), slots=[slot],
        cadence=CadenceType.HALF, profile_id="custom", layout=Layout.OPEN_SCORE,
        tempo=72, title="Round trip", seed=2026,
    )


def test_problem_round_trip_preserves_constraints_and_metadata(tmp_path):
    original = rich_problem()
    restored = loads_problem(dumps_problem(original))
    assert problem_to_dict(restored) == problem_to_dict(original)
    assert restored.slots[0].voice(Voice.SOPRANO).clef == Clef.TREBLE
    assert restored.slots[0].harmony.forbidden_harmonies == ("Ger+6",)

    path = tmp_path / "exercise.json"
    save_problem(path, original)
    assert problem_to_dict(load_problem(path)) == problem_to_dict(original)


def test_custom_profile_round_trip_preserves_rules_ranges_weights_and_options():
    profile = custom_profile(name="Studio policy")
    profile.severities[RuleCode.PARALLEL_FOURTH] = RuleSeverity.HARD_ERROR
    profile.severities[RuleCode.HIDDEN_FIFTH] = RuleSeverity.SOFT_PENALTY
    profile.weights["total_motion"] = 3.25
    profile.permit_voice_unisons = False
    restored = profile_from_dict(profile_to_dict(profile))
    assert restored.name == "Studio policy"
    assert restored.severity(RuleCode.PARALLEL_FOURTH) == RuleSeverity.HARD_ERROR
    assert restored.severity(RuleCode.HIDDEN_FIFTH) == RuleSeverity.SOFT_PENALTY
    assert restored.weights["total_motion"] == 3.25
    assert not restored.permit_voice_unisons


@pytest.mark.parametrize("payload, expected", [
    ({}, "schema version"),
    ({"schema_version": 99, "kind": "part-writing-problem"}, "schema version"),
    ({"schema_version": 1, "kind": "wrong"}, "Expected"),
    ({"schema_version": 1, "kind": "part-writing-problem", "slots": [],
      "meter": [0, 4]}, "meter"),
])
def test_invalid_documents_fail_with_clear_schema_errors(payload, expected):
    with pytest.raises(SerializationError, match=expected):
        problem_from_dict(payload)


def test_malformed_json_is_rejected_without_eval_or_pickle():
    with pytest.raises(SerializationError, match="Malformed JSON"):
        loads_problem("{'not': valid json}")
    parsed = json.loads(dumps_problem(rich_problem()))
    assert parsed["kind"] == "part-writing-problem"
