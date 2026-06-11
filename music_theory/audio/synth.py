"""Dependency-free additive synth backend.

Renders note events to a float32 stereo buffer using a small harmonic stack and
a piano-ish percussive envelope. Always available - the app never loses audio
even if fluidsynth/soundfonts are missing."""

from __future__ import annotations

from functools import lru_cache
from typing import Sequence

import numpy as np

from .events import total_duration

SAMPLE_RATE = 44100
_RELEASE = 0.18  # seconds of decay tail after note end

# Relative amplitudes of harmonics 1..6 - a mellow, piano-leaning spectrum.
_HARMONICS = np.array([1.0, 0.45, 0.30, 0.15, 0.08, 0.05], dtype=np.float32)


def midi_to_freq(midi: float) -> float:
    return 440.0 * (2.0 ** ((midi - 69.0) / 12.0))


def _envelope(n_samples: int, sr: int) -> np.ndarray:
    """Fast attack + exponential decay (struck-string feel)."""
    t = np.arange(n_samples, dtype=np.float32) / sr
    attack = 0.006
    env = np.ones(n_samples, dtype=np.float32)
    a = int(attack * sr)
    if a > 0:
        env[:a] = np.linspace(0.0, 1.0, a, dtype=np.float32)
    env *= np.exp(-2.2 * t).astype(np.float32)
    return env


@lru_cache(maxsize=512)
def _render_note(midi: int, dur: float, vel: int, sr: int) -> np.ndarray:
    """Memoized note renderer. Exercises reuse a small set of (pitch, duration,
    velocity) combinations heavily - replays and arpeggios become near-free.
    Callers only read the returned buffer (it is mixed into a fresh output
    array), so sharing one cached instance is safe."""
    return _render_note_uncached(midi, dur, vel, sr)


def _render_note_uncached(midi: int, dur: float, vel: int, sr: int) -> np.ndarray:
    freq = midi_to_freq(midi)
    length = max(1, int((dur + _RELEASE) * sr))
    t = np.arange(length, dtype=np.float32) / sr
    wave = np.zeros(length, dtype=np.float32)
    for i, amp in enumerate(_HARMONICS, start=1):
        if freq * i > sr / 2:  # avoid aliasing above Nyquist
            break
        wave += amp * np.sin(2.0 * np.pi * freq * i * t)
    wave *= _envelope(length, sr)
    gain = (vel / 127.0) * 0.18
    return (wave * gain).astype(np.float32)


class SynthBackend:
    name = "synth"
    available = True

    def __init__(self, sample_rate: int = SAMPLE_RATE) -> None:
        self.sr = sample_rate

    def render(self, events: Sequence[dict], program: int = 0) -> np.ndarray:
        if not events:
            return np.zeros((1, 2), dtype=np.float32)
        end = total_duration(events) + _RELEASE
        n = int(end * self.sr) + 1
        mono = np.zeros(n, dtype=np.float32)
        for ev in events:
            seg = _render_note(int(ev["midi"]), round(float(ev["dur"]), 4),
                               int(ev.get("vel", 96)), self.sr)
            start = int(ev["start"] * self.sr)
            stop = min(start + seg.shape[0], n)
            mono[start:stop] += seg[: stop - start]
        peak = float(np.max(np.abs(mono))) if mono.size else 0.0
        if peak > 0.99:
            mono *= 0.99 / peak
        return np.column_stack([mono, mono])

    def close(self) -> None:  # symmetry with fluid backend
        pass
