"""Portable offline assignments and locally regradable response reports."""
from __future__ import annotations

from dataclasses import fields
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import random

from .base import Exercise, InputMode
from .registry import generate
from ..theory.pitch import Note
from ..theory.practice_tools import WORKSHEET_TYPES

ASSIGNMENT_TYPES = WORKSHEET_TYPES + (
    "jazz_ii_v_i", "jazz_guide_tones", "jazz_tritone_sub", "jazz_progression_ear", "play_jazz_shell",
    "interval_recognition", "chord_quality_ear", "scale_mode_ear", "melodic_dictation",
    "play_note", "play_interval", "play_triad", "play_scale",
)
MAX_FILE = 2 * 1024 * 1024


def _plain(value):
    if isinstance(value, Note):
        return {"$note": value.name}
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_plain(v) for v in (sorted(value) if isinstance(value, set) else value)]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise ValueError(f"Unsupported assignment value: {type(value).__name__}")


def _restore(value, depth=0):
    if depth > 20:
        raise ValueError("Assignment data is nested too deeply.")
    if isinstance(value, dict):
        if set(value) == {"$note"}:
            note = Note.parse(value["$note"])
            if not 0 <= note.midi <= 127:
                raise ValueError("Assignment note lies outside MIDI range.")
            return note
        return {k: _restore(v, depth + 1) for k, v in value.items()}
    if isinstance(value, list):
        return [_restore(v, depth + 1) for v in value]
    return value


def pack_exercise(ex: Exercise) -> dict:
    if ex.checker is not None:
        raise ValueError("This exercise uses a custom checker and cannot be exchanged yet.")
    return {f.name: _plain(getattr(ex, f.name)) for f in fields(ex) if f.name != "checker"}


def unpack_exercise(data: dict) -> Exercise:
    if not isinstance(data, dict) or data.get("etype") not in ASSIGNMENT_TYPES or "checker" in data:
        raise ValueError("Unsupported exercise in assignment file.")
    allowed = {f.name for f in fields(Exercise)} - {"checker"}
    if set(data) - allowed:
        raise ValueError("Unknown exercise fields in assignment.")
    restored = _restore(data)
    restored["input_mode"] = InputMode(restored["input_mode"])
    if not isinstance(restored.get("prompt"), str) or len(restored["prompt"]) > 10000:
        raise ValueError("Invalid assignment prompt.")
    ex = Exercise(**restored)
    if not ex.grade(ex.answer):
        raise ValueError("Assignment contains an inconsistent answer key.")
    # Shared exercise audio/rendering expects bounded, real music values.
    _validate_payload(data)
    _validate_play(ex.play)
    if len(ex.choices) > 12 or not all(isinstance(c, str) for c in ex.choices):
        raise ValueError("Assignment choices must be a short text list.")
    for name in ("prompt", "explanation", "teach", "hint"):
        setattr(ex, name, escape(str(getattr(ex, name))))
    return ex


def _validate_play(spec):
    if spec is None:
        return
    if not isinstance(spec, dict):
        raise ValueError("Invalid audio specification.")
    mode = spec.get("mode")
    if mode not in ("melody", "interval", "chord", "harmonic", "note"):
        raise ValueError("Unsupported assignment audio mode.")
    for field, low, high in (("tempo", 20, 300), ("beats", .05, 8), ("dur", .05, 8)):
        value = spec.get(field, 90 if field == "tempo" else 1)
        if not isinstance(value, (int, float)) or not low <= value <= high:
            raise ValueError("Assignment audio timing is out of range.")
    if mode == "harmonic":
        chords = spec.get("chords", [])
        if not 1 <= len(chords) <= 16 or any(not isinstance(c, list) or not 1 <= len(c) <= 12 for c in chords):
            raise ValueError("Assignment harmony is too large.")
        notes = [n for c in chords for n in c]
    elif mode == "interval":
        notes = [spec.get("low"), spec.get("high")]
    elif mode == "note":
        notes = [spec.get("midi")]
    else:
        notes = spec.get("midis", [])
    if not isinstance(notes, list) or not 1 <= len(notes) <= 192 or any(type(n) is not int or not 0 <= n <= 127 for n in notes):
        raise ValueError("Assignment audio contains invalid notes.")
    if mode == "chord" and len(notes) > 12:
        raise ValueError("Assignment chords support at most 12 notes.")
    attacks = len(spec.get("chords", [])) if mode == "harmonic" else len(notes) if mode == "melody" else 1
    if attacks * spec.get("beats", 2 if mode == "harmonic" else 1) * 60 / spec.get("tempo", 90) > 60:
        raise ValueError("Assignment audio must be at most one minute.")


def _validate_payload(value, depth=0):
    import math
    if depth > 20:
        raise ValueError("Assignment is nested too deeply.")
    if isinstance(value, (list, dict)) and len(value) > 512:
        raise ValueError("Assignment collection is too large.")
    if isinstance(value, dict):
        for k, v in value.items():
            if k in ("tempo",) and (not isinstance(v, (float, int)) or not 20 <= v <= 300):
                raise ValueError("Audio tempo must be 20–300 BPM.")
            _validate_payload(v, depth + 1)
    elif isinstance(value, list):
        for v in value:
            _validate_payload(v, depth + 1)
    elif isinstance(value, float) and not math.isfinite(value):
        raise ValueError("Assignment contains a non-finite number.")
    elif isinstance(value, str) and len(value) > 10000:
        raise ValueError("Assignment text is too long.")


def assignment_id(assignment: dict) -> str:
    content = {k: v for k, v in assignment.items() if k != "id"}
    return sha256(json.dumps(content, sort_keys=True, ensure_ascii=True, allow_nan=False).encode()).hexdigest()[:20]


def create_assignment(title: str, types: list[str], difficulty: float, count: int, seed: int) -> dict:
    if not 1 <= len(title.strip()) <= 160 or not types or any(t not in ASSIGNMENT_TYPES for t in types):
        raise ValueError("Enter a short title and choose supported topics.")
    if not 1 <= count <= 50 or not 0 <= difficulty <= 10:
        raise ValueError("Use 1–50 questions and difficulty 0–10.")
    rng = random.Random(seed)
    items = [pack_exercise(generate(types[i % len(types)], difficulty, rng)) for i in range(count)]
    result = {"format": "mtm-assignment", "schema": 1, "title": title.strip(), "items": items}
    result["id"] = assignment_id(result)
    return result


def save_json(path: Path, data: dict):
    encoded = json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)
    if len(encoded.encode()) > MAX_FILE:
        raise ValueError("Assignment/result file exceeds 2 MB.")
    Path(path).write_text(encoded, encoding="utf-8")


def read_json(path: Path) -> dict:
    if Path(path).stat().st_size > MAX_FILE:
        raise ValueError("Assignment/result files are limited to 2 MB.")
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Expected an assignment or result object.")
    _validate_payload(data)
    return data


def load_assignment(path: Path) -> tuple[dict, list[Exercise]]:
    data = read_json(path)
    if data.get("format") != "mtm-assignment" or data.get("schema") != 1 or data.get("id") != assignment_id(data):
        raise ValueError("Unknown format or inconsistent assignment identifier.")
    if not isinstance(data.get("items"), list) or not 1 <= len(data["items"]) <= 50:
        raise ValueError("An assignment must contain 1–50 questions.")
    return data, [unpack_exercise(item) for item in data["items"]]


def make_result(assignment: dict, learner: str, responses: list) -> dict:
    if len(responses) != len(assignment["items"]):
        raise ValueError("Complete every question before exporting a result.")
    marks = [unpack_exercise(item).grade(answer) for item, answer in zip(assignment["items"], responses)]
    return {"format": "mtm-result", "schema": 1, "assignment_id": assignment["id"],
            "learner": learner[:160], "responses": _plain(responses), "correct": sum(marks), "total": len(marks),
            "notice": "Offline practice report. Identity and testing conditions are not verified."}


def check_result(assignment: dict, result: dict) -> dict:
    if result.get("format") != "mtm-result" or result.get("schema") != 1 or result.get("assignment_id") != assignment["id"]:
        raise ValueError("This result does not belong to the loaded assignment.")
    return make_result(assignment, str(result.get("learner", "")), result.get("responses", []))
