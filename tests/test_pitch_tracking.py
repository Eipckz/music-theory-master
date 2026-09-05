import numpy as np
import pytest
from scipy.io import wavfile

from music_theory.audio.pitch_tracking import track_pitch, intonation_report, compare_melody, load_wav


@pytest.mark.parametrize("midi", [36, 48, 60, 69, 79])
def test_harmonic_single_voice_pitch(midi):
    sr = 44100
    t = np.arange(sr) / sr
    f = 440 * 2 ** ((midi - 69) / 12)
    signal = .25 * np.sin(2 * np.pi * f * t) + .35 * np.sin(4 * np.pi * f * t) + .1 * np.sin(6 * np.pi * f * t)
    report = intonation_report(track_pitch(signal, sr), midi)
    assert abs(report["median_cents"]) < 8
    assert report["within_percent"] > 95


def test_silence_noise_and_octave_error():
    silent = track_pitch(np.zeros(16000), 16000)
    assert intonation_report(silent, 60)["voiced_frames"] == 0
    noisy = track_pitch(np.random.default_rng(2).normal(0, .1, 16000), 16000)
    assert intonation_report(noisy, 60)["voiced_frames"] == 0
    t = np.arange(16000) / 16000
    frames = track_pitch(.3 * np.sin(2 * np.pi * 880 * t), 16000)
    assert intonation_report(frames, 69)["median_cents"] > 1190
    assert not compare_melody(silent, [(0, 1, 60)])[0]["matched"]


def test_short_recording_cannot_complete_long_target_note():
    t = np.arange(16000) / 16000
    frames = track_pitch(.3 * np.sin(2 * np.pi * 440 * t), 16000)
    result = compare_melody(frames, [(0, 5, 69)])[0]
    assert not result["matched"] and result["voiced_fraction"] < .25


def test_melody_alignment_and_wav_roundtrip(tmp_path):
    sr = 16000
    t = np.arange(sr) / sr
    signal = np.concatenate([.3 * np.sin(2 * np.pi * hz * t) for hz in (440, 493.8833)])
    path = tmp_path / "voice.wav"
    wavfile.write(path, sr, (signal * 32767).astype(np.int16))
    samples, rate = load_wav(path)
    result = compare_melody(track_pitch(samples, rate), [(0, 1, 69), (1, 1, 71)])
    assert all(r["matched"] for r in result)


def test_invalid_audio():
    with pytest.raises(ValueError):
        track_pitch(np.array([np.nan] * 2000), 16000)
