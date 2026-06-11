"""Helpers that turn musical intent into timed note events.

An *event* is a dict: {"start": seconds, "dur": seconds, "midi": int, "vel": int}.
Both audio backends consume the same event list, so callers never care which
synthesizer is active."""

from __future__ import annotations

from typing import Iterable, Sequence


def beats_to_seconds(beats: float, tempo_bpm: float) -> float:
    return float(beats) * 60.0 / float(tempo_bpm)


def melody_events(
    midis: Sequence[int],
    *,
    tempo_bpm: float = 90.0,
    beats_per_note: float = 1.0,
    gap: float = 0.04,
    velocity: int = 96,
) -> list[dict]:
    """Sequential single notes (a melody)."""
    step = beats_to_seconds(beats_per_note, tempo_bpm)
    dur = max(0.05, step - gap)
    events = []
    for i, m in enumerate(midis):
        events.append({"start": i * step, "dur": dur, "midi": int(m), "vel": velocity})
    return events


def chord_events(
    midis: Iterable[int],
    *,
    start: float = 0.0,
    dur: float = 1.5,
    velocity: int = 88,
) -> list[dict]:
    """Simultaneous notes (a chord)."""
    return [
        {"start": start, "dur": dur, "midi": int(m), "vel": velocity} for m in midis
    ]


def sequence_events(
    items: Sequence[tuple],
    *,
    tempo_bpm: float = 90.0,
    velocity: int = 90,
) -> list[dict]:
    """A sequence of (midi_or_list, beats) pairs played back to back.

    midi_or_list may be a single midi int or an iterable of midis (a chord)."""
    events: list[dict] = []
    t = 0.0
    for pitch, beats in items:
        dur = beats_to_seconds(beats, tempo_bpm)
        play = max(0.05, dur - 0.04)
        if isinstance(pitch, (list, tuple, set)):
            for m in pitch:
                events.append({"start": t, "dur": play, "midi": int(m), "vel": velocity})
        elif pitch is not None:
            events.append({"start": t, "dur": play, "midi": int(pitch), "vel": velocity})
        t += dur
    return events


def total_duration(events: Sequence[dict]) -> float:
    if not events:
        return 0.0
    return max(e["start"] + e["dur"] for e in events)
