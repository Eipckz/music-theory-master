"""Versioned, validated JSON interchange for part-writing artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from ..pitch import Note
from .models import (
    CadenceType, ChordFactor, Clef, HarmonyConstraint, HarmonySlot, Layout,
    PartWritingProblem, PartWritingSolution, PitchConstraint, RuleEvaluation,
    VOICE_ORDER, VoiceConstraint, VoiceRange, Voicing,
)
from .profiles import RuleProfile


SCHEMA_VERSION = 1


class SerializationError(ValueError):
    pass


def _note(note: Note | None) -> str | None:
    return note.name if note is not None else None


def _parse_note(value, field: str) -> Note | None:
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise SerializationError(f"{field} must be a note name string")
    try:
        return Note.parse(value)
    except ValueError as exc:
        raise SerializationError(f"{field}: {exc}") from exc


def _enum(enum_type, value, field: str, *, optional: bool = False):
    if optional and value in (None, ""):
        return None
    try:
        return enum_type(value)
    except (TypeError, ValueError) as exc:
        raise SerializationError(f"Invalid {field}: {value!r}") from exc


def pitch_constraint_to_dict(value: PitchConstraint) -> dict:
    return {
        "exact": _note(value.exact),
        "pitch_class": _note(value.pitch_class),
        "scale_degree": value.scale_degree,
        "chord_factor": value.chord_factor.value if value.chord_factor else None,
        "allowed_pitches": [_note(note) for note in value.allowed_pitches],
        "minimum": _note(value.minimum),
        "maximum": _note(value.maximum),
    }


def pitch_constraint_from_dict(data: dict, field: str) -> PitchConstraint:
    if not isinstance(data, dict):
        raise SerializationError(f"{field} must be an object")
    degree = data.get("scale_degree")
    if degree is not None and (not isinstance(degree, int) or not 1 <= degree <= 7):
        raise SerializationError(f"{field}.scale_degree must be 1 through 7")
    allowed = data.get("allowed_pitches", [])
    if not isinstance(allowed, list):
        raise SerializationError(f"{field}.allowed_pitches must be a list")
    return PitchConstraint(
        exact=_parse_note(data.get("exact"), f"{field}.exact"),
        pitch_class=_parse_note(data.get("pitch_class"), f"{field}.pitch_class"),
        scale_degree=degree,
        chord_factor=_enum(ChordFactor, data.get("chord_factor"),
                           f"{field}.chord_factor", optional=True),
        allowed_pitches=tuple(_parse_note(item, f"{field}.allowed_pitches") for item in allowed),
        minimum=_parse_note(data.get("minimum"), f"{field}.minimum"),
        maximum=_parse_note(data.get("maximum"), f"{field}.maximum"),
    )


def voice_constraint_to_dict(value: VoiceConstraint) -> dict:
    return {
        "pitch": pitch_constraint_to_dict(value.pitch),
        "locked": value.locked,
        "clef": value.clef.value if value.clef else None,
        "note": value.note,
        "source_label": value.source_label,
    }


def voice_constraint_from_dict(data: dict, field: str) -> VoiceConstraint:
    if not isinstance(data, dict):
        raise SerializationError(f"{field} must be an object")
    locked = data.get("locked", False)
    if not isinstance(locked, bool):
        raise SerializationError(f"{field}.locked must be true or false")
    return VoiceConstraint(
        pitch=pitch_constraint_from_dict(data.get("pitch", {}), f"{field}.pitch"),
        locked=locked,
        clef=_enum(Clef, data.get("clef"), f"{field}.clef", optional=True),
        note=str(data.get("note", "")), source_label=str(data.get("source_label", "")),
    )


def harmony_constraint_to_dict(value: HarmonyConstraint) -> dict:
    return {
        "roman_numeral": value.roman_numeral,
        "chord_symbol": value.chord_symbol,
        "figured_bass": value.figured_bass,
        "inversion": value.inversion,
        "exact_bass_pitch": _note(value.exact_bass_pitch),
        "required_chord_tones": list(value.required_chord_tones),
        "forbidden_chord_tones": list(value.forbidden_chord_tones),
        "required_doubling": value.required_doubling.value if value.required_doubling else None,
        "allowed_harmonies": list(value.allowed_harmonies),
        "forbidden_harmonies": list(value.forbidden_harmonies),
    }


def harmony_constraint_from_dict(data: dict, field: str) -> HarmonyConstraint:
    if not isinstance(data, dict):
        raise SerializationError(f"{field} must be an object")
    inversion = data.get("inversion")
    if inversion is not None and (not isinstance(inversion, int) or not 0 <= inversion <= 3):
        raise SerializationError(f"{field}.inversion must be 0 through 3")
    list_fields = ("required_chord_tones", "forbidden_chord_tones", "allowed_harmonies",
                   "forbidden_harmonies")
    for name in list_fields:
        if not isinstance(data.get(name, []), list):
            raise SerializationError(f"{field}.{name} must be a list")
    return HarmonyConstraint(
        roman_numeral=data.get("roman_numeral") or None,
        chord_symbol=data.get("chord_symbol") or None,
        figured_bass=data.get("figured_bass") or None,
        inversion=inversion,
        exact_bass_pitch=_parse_note(data.get("exact_bass_pitch"),
                                     f"{field}.exact_bass_pitch"),
        required_chord_tones=tuple(str(item) for item in data.get("required_chord_tones", [])),
        forbidden_chord_tones=tuple(str(item) for item in data.get("forbidden_chord_tones", [])),
        required_doubling=_enum(ChordFactor, data.get("required_doubling"),
                                f"{field}.required_doubling", optional=True),
        allowed_harmonies=tuple(str(item) for item in data.get("allowed_harmonies", [])),
        forbidden_harmonies=tuple(
            str(item) for item in data.get("forbidden_harmonies", [])),
    )


def problem_to_dict(problem: PartWritingProblem) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "part-writing-problem",
        "key_tonic": problem.key_tonic,
        "mode": problem.mode,
        "meter": list(problem.meter),
        "cadence": problem.cadence.value if problem.cadence else None,
        "profile_id": problem.profile_id,
        "layout": problem.layout.value,
        "tempo": problem.tempo,
        "title": problem.title,
        "seed": problem.seed,
        "slots": [
            {
                "harmony": harmony_constraint_to_dict(slot.harmony),
                "voices": {voice.value: voice_constraint_to_dict(slot.voice(voice))
                           for voice in VOICE_ORDER},
                "duration": slot.duration,
                "cadence_role": slot.cadence_role,
                "label": slot.label,
            }
            for slot in problem.slots
        ],
    }


def _validate_header(data: dict, kind: str) -> None:
    if not isinstance(data, dict):
        raise SerializationError("The document root must be an object")
    if data.get("schema_version") != SCHEMA_VERSION:
        raise SerializationError(
            f"Unsupported schema version {data.get('schema_version')!r}; expected {SCHEMA_VERSION}")
    if data.get("kind") != kind:
        raise SerializationError(f"Expected {kind!r}, got {data.get('kind')!r}")


def problem_from_dict(data: dict) -> PartWritingProblem:
    _validate_header(data, "part-writing-problem")
    meter = data.get("meter", [4, 4])
    if (not isinstance(meter, list) or len(meter) != 2
            or not all(isinstance(item, int) and item > 0 for item in meter)):
        raise SerializationError("meter must contain two positive integers")
    raw_slots = data.get("slots")
    if not isinstance(raw_slots, list):
        raise SerializationError("slots must be a list")
    slots = []
    for index, raw in enumerate(raw_slots):
        if not isinstance(raw, dict):
            raise SerializationError(f"slots[{index}] must be an object")
        voices_data = raw.get("voices", {})
        if not isinstance(voices_data, dict):
            raise SerializationError(f"slots[{index}].voices must be an object")
        voices = {
            voice: voice_constraint_from_dict(
                voices_data.get(voice.value, {}), f"slots[{index}].voices.{voice.value}")
            for voice in VOICE_ORDER
        }
        duration = raw.get("duration", 1.0)
        if not isinstance(duration, (int, float)) or isinstance(duration, bool) or duration <= 0:
            raise SerializationError(f"slots[{index}].duration must be positive")
        slots.append(HarmonySlot(
            harmony=harmony_constraint_from_dict(
                raw.get("harmony", {}), f"slots[{index}].harmony"),
            voices=voices, duration=float(duration),
            cadence_role=str(raw.get("cadence_role", "")),
            label=str(raw.get("label", "")),
        ))
    tempo = data.get("tempo", 84)
    seed = data.get("seed", 0)
    if not isinstance(tempo, int) or not 20 <= tempo <= 300:
        raise SerializationError("tempo must be an integer from 20 to 300")
    if not isinstance(seed, int):
        raise SerializationError("seed must be an integer")
    return PartWritingProblem(
        key_tonic=str(data.get("key_tonic", "C")),
        mode=str(data.get("mode", "major")), meter=(meter[0], meter[1]), slots=slots,
        cadence=_enum(CadenceType, data.get("cadence"), "cadence", optional=True),
        profile_id=str(data.get("profile_id", "common-practice")),
        layout=_enum(Layout, data.get("layout", "chorale"), "layout"),
        tempo=tempo, title=str(data.get("title", "Part-writing exercise")), seed=seed,
    )


def profile_to_dict(profile: RuleProfile) -> dict:
    return {
        "schema_version": SCHEMA_VERSION, "kind": "part-writing-profile",
        "id": profile.id, "name": profile.name, "description": profile.description,
        "severities": {code.value: severity.value for code, severity in profile.severities.items()},
        "weights": dict(profile.weights),
        "voice_ranges": {voice.value: {"minimum": rng.minimum.name,
                                        "maximum": rng.maximum.name}
                         for voice, rng in profile.voice_ranges.items()},
        "options": {
            "max_melodic_leap": profile.max_melodic_leap,
            "large_leap_threshold": profile.large_leap_threshold,
            "max_tenor_bass_spacing": profile.max_tenor_bass_spacing,
            "require_complete_triads": profile.require_complete_triads,
            "allow_incomplete_dominant_seventh": profile.allow_incomplete_dominant_seventh,
            "permit_voice_unisons": profile.permit_voice_unisons,
            "treat_compound_perfects": profile.treat_compound_perfects,
            "permit_unequal_fifths": profile.permit_unequal_fifths,
            "inner_leading_tone_exception": profile.inner_leading_tone_exception,
            "strict_hidden_perfects": profile.strict_hidden_perfects,
            "strict_cadential_soprano": profile.strict_cadential_soprano,
        },
    }


def profile_from_dict(data: dict) -> RuleProfile:
    from .models import RuleCode, RuleSeverity
    _validate_header(data, "part-writing-profile")
    raw_severities = data.get("severities", {})
    raw_weights = data.get("weights", {})
    raw_ranges = data.get("voice_ranges", {})
    options = data.get("options", {})
    if not all(isinstance(item, dict) for item in
               (raw_severities, raw_weights, raw_ranges, options)):
        raise SerializationError("Profile sections must be objects")
    severities = {}
    for raw_code, raw_severity in raw_severities.items():
        severities[_enum(RuleCode, raw_code, "rule code")] = _enum(
            RuleSeverity, raw_severity, "rule severity")
    weights = {}
    for name, value in raw_weights.items():
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise SerializationError(f"Weight {name!r} must be numeric")
        weights[str(name)] = float(value)
    ranges = {}
    for voice in VOICE_ORDER:
        raw = raw_ranges.get(voice.value)
        if not isinstance(raw, dict):
            raise SerializationError(f"Missing voice range for {voice.value}")
        minimum = _parse_note(raw.get("minimum"), f"voice_ranges.{voice.value}.minimum")
        maximum = _parse_note(raw.get("maximum"), f"voice_ranges.{voice.value}.maximum")
        if minimum is None or maximum is None or minimum.midi > maximum.midi:
            raise SerializationError(f"Invalid voice range for {voice.value}")
        ranges[voice] = VoiceRange(minimum, maximum)
    return RuleProfile(
        id=str(data.get("id", "custom")), name=str(data.get("name", "Custom")),
        description=str(data.get("description", "")), severities=severities,
        weights=weights, voice_ranges=ranges,
        max_melodic_leap=int(options.get("max_melodic_leap", 9)),
        large_leap_threshold=int(options.get("large_leap_threshold", 5)),
        max_tenor_bass_spacing=int(options.get("max_tenor_bass_spacing", 19)),
        require_complete_triads=bool(options.get("require_complete_triads", True)),
        allow_incomplete_dominant_seventh=bool(
            options.get("allow_incomplete_dominant_seventh", True)),
        permit_voice_unisons=bool(options.get("permit_voice_unisons", True)),
        treat_compound_perfects=bool(options.get("treat_compound_perfects", True)),
        permit_unequal_fifths=bool(options.get("permit_unequal_fifths", True)),
        inner_leading_tone_exception=bool(options.get("inner_leading_tone_exception", False)),
        strict_hidden_perfects=bool(options.get("strict_hidden_perfects", False)),
        strict_cadential_soprano=bool(options.get("strict_cadential_soprano", True)),
    )


def solution_to_dict(solution: PartWritingSolution) -> dict:
    return {
        "schema_version": SCHEMA_VERSION, "kind": "part-writing-solution",
        "voicings": [[note.name for note in voicing.notes] for voicing in solution.voicings],
        "score": solution.score,
        "score_breakdown": dict(solution.score_breakdown),
        "harmony_labels": list(solution.harmony_labels),
    }


def solution_from_dict(data: dict) -> PartWritingSolution:
    _validate_header(data, "part-writing-solution")
    raw = data.get("voicings")
    if not isinstance(raw, list):
        raise SerializationError("voicings must be a list")
    voicings = []
    for index, item in enumerate(raw):
        if not isinstance(item, list) or len(item) != 4:
            raise SerializationError(f"voicings[{index}] must contain SATB pitches")
        notes = [_parse_note(value, f"voicings[{index}]") for value in item]
        if any(note is None for note in notes):
            raise SerializationError(f"voicings[{index}] cannot contain blank pitches")
        voicings.append(Voicing(*notes))
    score = data.get("score", 0.0)
    breakdown = data.get("score_breakdown", {})
    labels = data.get("harmony_labels", [])
    if not isinstance(score, (int, float)) or isinstance(score, bool):
        raise SerializationError("score must be numeric")
    if not isinstance(breakdown, dict) or not isinstance(labels, list):
        raise SerializationError("score_breakdown must be an object and harmony_labels a list")
    return PartWritingSolution(voicings, float(score),
                               {str(k): float(v) for k, v in breakdown.items()},
                               RuleEvaluation(), [str(label) for label in labels])


def dumps_problem(problem: PartWritingProblem) -> str:
    return json.dumps(problem_to_dict(problem), indent=2, ensure_ascii=False)


def loads_problem(text: str) -> PartWritingProblem:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SerializationError(f"Malformed JSON: {exc}") from exc
    return problem_from_dict(data)


def save_problem(path: str | Path, problem: PartWritingProblem) -> None:
    destination = Path(path)
    destination.write_text(dumps_problem(problem), encoding="utf-8")


def load_problem(path: str | Path) -> PartWritingProblem:
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise SerializationError(str(exc)) from exc
    return loads_problem(text)
