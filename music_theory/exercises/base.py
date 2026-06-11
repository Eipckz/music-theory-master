"""Exercise data model, answer grading, and audio playback dispatch."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional, Sequence


class InputMode(str, Enum):
    MULTIPLE_CHOICE = "multiple_choice"
    TEXT = "text"
    NOTE_ENTRY = "note_entry"      # place pitches (dictation) - list of midis
    PIANO = "piano"                # play pitches on keyboard - set/list of midis
    RHYTHM = "rhythm"              # tapped/selected durations
    SEQUENCE = "sequence"          # ordered list of labels (e.g. row forms)
    MULTI_VOICE = "multi_voice"    # several simultaneous lines - list of midi lists


def normalize_answer(value: Any) -> str:
    return str(value).strip().lower().replace(" ", "").replace("\u266f", "#").replace("\u266d", "b")


@dataclass
class Exercise:
    skill_id: str
    domain: str                         # theory | aural | piano
    etype: str                          # generator type id
    prompt: str
    input_mode: InputMode
    answer: Any                         # canonical answer (str | list | set)
    choices: list[str] = field(default_factory=list)
    explanation: str = ""
    teach: str = ""                     # concept explanation shown on a wrong answer
    hint: str = ""                      # optional pre-answer nudge
    difficulty: float = 1.0
    play: Optional[dict] = None         # audio spec (see render_play)
    reveal: Optional[dict] = None       # what to show on reveal (e.g. {'notes': [...]})
    checker: Optional[Callable[[Any, Any], bool]] = None
    tags: dict = field(default_factory=dict)

    def grade(self, response: Any) -> bool:
        if self.checker is not None:
            return bool(self.checker(response, self.answer))
        if self.input_mode in (InputMode.MULTIPLE_CHOICE, InputMode.TEXT):
            return _grade_scalar(response, self.answer)
        if self.input_mode in (InputMode.NOTE_ENTRY, InputMode.SEQUENCE):
            return _grade_sequence(response, self.answer, self.tags.get("match", "exact"))
        if self.input_mode == InputMode.PIANO:
            return _grade_set(response, self.answer, self.tags.get("match", "pc"))
        if self.input_mode == InputMode.RHYTHM:
            return _grade_sequence(response, self.answer, "exact")
        if self.input_mode == InputMode.MULTI_VOICE:
            return _grade_voices(response, self.answer, self.tags.get("match", "exact"))
        return False


def _grade_scalar(response: Any, answer: Any) -> bool:
    if isinstance(answer, (list, set, tuple)):
        return normalize_answer(response) in {normalize_answer(a) for a in answer}
    return normalize_answer(response) == normalize_answer(answer)


def _grade_sequence(response: Any, answer: Any, match: str) -> bool:
    r = list(response or [])
    a = list(answer or [])
    if len(r) != len(a):
        return False
    if match == "pc":
        return [int(x) % 12 for x in r] == [int(x) % 12 for x in a]
    if match == "exact":
        return [_as_cmp(x) for x in r] == [_as_cmp(x) for x in a]
    return [normalize_answer(x) for x in r] == [normalize_answer(x) for x in a]


def _grade_set(response: Any, answer: Any, match: str) -> bool:
    r = set(int(x) for x in (response or []))
    a = set(int(x) for x in (answer or []))
    if match == "pc":
        return {x % 12 for x in r} == {x % 12 for x in a}
    return r == a


def _grade_voices(response: Any, answer: Any, match: str) -> bool:
    """Every voice must match its expected line (same voice count and order)."""
    r = list(response or [])
    a = list(answer or [])
    if len(r) != len(a):
        return False
    return all(_grade_sequence(rv, av, match) for rv, av in zip(r, a))


def _as_cmp(x: Any) -> Any:
    if hasattr(x, "midi"):
        return int(x.midi)
    if isinstance(x, (int, float)):
        return int(x)
    return normalize_answer(x)


# ---------------------------------------------------------------------------
# Audio playback dispatch
# ---------------------------------------------------------------------------
def render_play(engine, spec: Optional[dict], *, block: bool = False):
    """Play an exercise's audio spec on the given AudioEngine."""
    if not spec or engine is None:
        return None
    mode = spec.get("mode")
    tempo = spec.get("tempo", 90)
    if mode == "melody":
        return engine.play_melody(spec["midis"], tempo=tempo,
                                  beats_per_note=spec.get("beats", 1.0), block=block)
    if mode == "interval":
        return engine.play_interval(spec["low"], spec["high"],
                                    harmonic=spec.get("harmonic", False), tempo=tempo, block=block)
    if mode == "chord":
        return engine.play_chord(spec["midis"], arpeggiate=spec.get("arpeggiate", False),
                                 tempo=tempo, block=block)
    if mode == "sequence":
        return engine.play_sequence(spec["items"], tempo=tempo, block=block)
    if mode == "harmonic":
        items = [(ch, spec.get("beats", 2.0)) for ch in spec["chords"]]
        return engine.play_sequence(items, tempo=tempo, block=block)
    if mode == "note":
        return engine.play_note(spec["midi"], dur=spec.get("dur", 1.2), block=block)
    return None
