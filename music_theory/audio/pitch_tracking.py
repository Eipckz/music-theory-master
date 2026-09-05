"""Local monophonic pitch analysis with voiced/silent separation."""
from __future__ import annotations

from dataclasses import dataclass
from math import gcd
from pathlib import Path

import numpy as np
from scipy.signal import resample_poly
from scipy.io import wavfile


@dataclass(frozen=True)
class PitchFrame:
    time: float
    midi: float | None
    confidence: float
    rms: float


def mono_audio(samples, sample_rate: int) -> np.ndarray:
    if not 8000 <= sample_rate <= 192000:
        raise ValueError("Use audio sampled between 8 and 192 kHz.")
    raw = np.asarray(samples)
    if raw.ndim not in (1, 2) or (raw.ndim == 2 and raw.shape[1] > 8):
        raise ValueError("Choose a mono/stereo recording with at most eight channels.")
    if not .08 <= len(raw) / sample_rate <= 30:
        raise ValueError("Use a recording between 0.08 and 30 seconds.")
    if raw.dtype == np.uint8:
        data = (raw.astype(np.float64) - 128) / 128
    elif np.issubdtype(raw.dtype, np.signedinteger):
        data = raw.astype(np.float64) / (2 ** (8 * raw.dtype.itemsize - 1))
    else:
        data = raw.astype(np.float64)
    if not np.isfinite(data).all():
        raise ValueError("Audio contains non-finite samples.")
    if data.ndim == 2:
        data = data.mean(axis=1)
    return data


def load_wav(path: Path) -> tuple[np.ndarray, int]:
    if Path(path).stat().st_size > 48 * 1024 * 1024:
        raise ValueError("WAV files must be under 48 MB.")
    try:
        sr, samples = wavfile.read(path)
        return mono_audio(samples, int(sr)), int(sr)
    except Exception as exc:
        raise ValueError(f"Cannot read this WAV recording: {exc}") from exc


def _frame_pitch(frame: np.ndarray, sr: int) -> tuple[float | None, float, float]:
    data = frame - np.mean(frame)
    rms = float(np.sqrt(np.mean(data * data)))
    if rms < .004:
        return None, 0., rms
    n = len(data)
    low, high = max(2, int(sr / 1000)), min(int(sr / 60), n // 2)
    spectrum = np.fft.rfft(data, n=2 * n)
    ac = np.fft.irfft(spectrum * np.conj(spectrum))[:high + 1]
    energy = np.concatenate(([0.], np.cumsum(data * data)))
    lag = np.arange(high + 1)
    difference = np.maximum(0, energy[n - lag] + energy[n] - energy[lag] - 2 * ac)
    normalized = np.ones(high + 1)
    normalized[1:] = difference[1:] * lag[1:] / np.maximum(np.cumsum(difference[1:]), 1e-15)
    candidates = np.flatnonzero(normalized[low:high] < .15)
    if len(candidates):
        best = int(candidates[0] + low)
        while best + 1 < high and normalized[best + 1] < normalized[best]:
            best += 1
    else:
        best = int(np.argmin(normalized[low:high]) + low)
        if normalized[best] > .25:
            return None, max(0., 1 - float(normalized[best])), rms
    a, b, c = normalized[best - 1:best + 2]
    denominator = a - 2 * b + c
    shift = .5 * (a - c) / denominator if abs(denominator) > 1e-12 else 0.
    period = best + float(np.clip(shift, -.5, .5))
    frequency = sr / period
    return float(69 + 12 * np.log2(frequency / 440)), float(1 - b), rms


def track_pitch(samples, sample_rate: int) -> list[PitchFrame]:
    data = mono_audio(samples, sample_rate)
    sr = 16000
    factor = gcd(sample_rate, sr)
    if sample_rate != sr:
        data = resample_poly(data, sr // factor, sample_rate // factor)
    size, hop = 2048, 320
    if len(data) < size:
        data = np.pad(data, (0, size - len(data)))
    frames = []
    for start in range(0, len(data) - size + 1, hop):
        midi, confidence, rms = _frame_pitch(data[start:start + size], sr)
        frames.append(PitchFrame((start + size / 2) / sr, midi, confidence, rms))
    return frames


def intonation_report(frames: list[PitchFrame], target: int, tolerance: int = 35) -> dict:
    if not 0 <= target <= 127 or not 5 <= tolerance <= 100:
        raise ValueError("Choose a MIDI target and tolerance between 5 and 100 cents.")
    voiced = np.array([f.midi for f in frames if f.midi is not None], dtype=float)
    if not len(voiced):
        return {"voiced_frames": 0, "total_frames": len(frames), "message": "No stable monophonic pitch detected. Try a quieter room or a stronger single note."}
    cents = (voiced - target) * 100
    return {"voiced_frames": len(voiced), "total_frames": len(frames),
            "median_cents": round(float(np.median(cents)), 1),
            "within_percent": round(float(np.mean(np.abs(cents) <= tolerance) * 100), 1),
            "spread_cents": round(float(np.percentile(cents, 90) - np.percentile(cents, 10)), 1),
            "message": "Pitch estimate for a single voice/instrument; not a tone-quality or singing-technique grade."}


def compare_melody(frames: list[PitchFrame], expected: list[tuple[float, float, int]], *, offset: float = 0, tolerance: int = 50) -> list[dict]:
    """Compare aligned timed notes; silence never counts as a correct pitch."""
    if not expected or len(expected) > 256 or not -10 <= offset <= 10 or not 5 <= tolerance <= 100:
        raise ValueError("Use up to 256 target notes, an alignment offset ±10 seconds and tolerance 5–100 cents.")
    results = []
    for start, duration, midi in expected:
        if duration <= 0 or not 0 <= midi <= 127:
            raise ValueError("Invalid target melody.")
        # Exclude the edges to reduce window mixing at note boundaries.
        edge = min(.06, duration / 5)
        window = [f for f in frames if start + offset + edge <= f.time < start + offset + duration - edge]
        voiced = [f.midi for f in window if f.midi is not None]
        cents = float(np.median([(p - midi) * 100 for p in voiced])) if voiced else None
        # Missing recording time must count as missing evidence, too. Otherwise
        # a tiny fragment at the start of a long note could receive full credit.
        hops = [b.time - a.time for a, b in zip(frames, frames[1:]) if b.time > a.time]
        hop = float(np.median(hops)) if hops else .02
        expected_frames = max(1., (duration - 2 * edge) / hop)
        fraction = min(1., len(voiced) / max(len(window), expected_frames))
        results.append({"target": midi, "start": start, "median_cents": round(cents, 1) if cents is not None else None,
                        "voiced_fraction": round(fraction, 3),
                        "matched": cents is not None and abs(cents) <= tolerance and fraction >= .5})
    return results
