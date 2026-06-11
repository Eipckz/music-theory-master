"""Audio event modeling and synthesis (backend-agnostic, no device needed)."""

from __future__ import annotations

import numpy as np

from music_theory.audio import events as ev
from music_theory.audio.engine import AudioEngine
from music_theory.storage import Settings


def test_melody_event_timing():
    evs = ev.melody_events([60, 62, 64], tempo_bpm=120, beats_per_note=1.0)
    assert len(evs) == 3
    # at 120bpm a beat is 0.5s; third note starts at 1.0s
    assert abs(evs[2]["start"] - 1.0) < 1e-6
    assert ev.total_duration(evs) > 1.0


def test_chord_events_simultaneous():
    evs = ev.chord_events([60, 64, 67])
    assert {e["start"] for e in evs} == {0.0}
    assert len(evs) == 3


def _synth_engine(tmp_path):
    s = Settings(tmp_path / "s.json")
    s.set("audio_backend", "synth")
    return AudioEngine(s)


def test_synth_render_shape(tmp_path):
    eng = _synth_engine(tmp_path)
    assert eng.backend_name == "synth"
    buf = eng.render(ev.melody_events([60, 64, 67], tempo_bpm=120))
    assert isinstance(buf, np.ndarray)
    assert buf.dtype == np.float32
    assert buf.size > 0
    assert np.all(np.isfinite(buf))
    assert float(np.max(np.abs(buf))) <= 1.01
    eng.close()


def test_render_empty_is_safe(tmp_path):
    eng = _synth_engine(tmp_path)
    buf = eng.render([])
    assert isinstance(buf, np.ndarray)
    eng.close()


def test_volume_scaling(tmp_path):
    eng = _synth_engine(tmp_path)
    eng.settings.set("master_volume", 1.0)
    loud = eng.render(ev.chord_events([60, 64, 67]))
    eng.settings.set("master_volume", 0.25)
    soft = eng.render(ev.chord_events([60, 64, 67]))
    assert float(np.max(np.abs(soft))) < float(np.max(np.abs(loud))) + 1e-6
    eng.close()
