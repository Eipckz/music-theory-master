"""High-level audio engine.

Picks the best available backend (fluidsynth SoundFont, else numpy synth),
renders note events to a buffer, and plays it through sounddevice. Exposes
musical conveniences (note/interval/chord/melody/metronome) used across the UI
and exercise players."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Optional, Sequence

import numpy as np

from . import events as ev
from .synth import SAMPLE_RATE, SynthBackend

try:
    import sounddevice as _sd
except Exception:  # noqa: BLE001 - audio output is optional in headless tests
    _sd = None


@dataclass
class Note:
    midi: int
    beats: float = 1.0
    velocity: int = 96


class AudioEngine:
    def __init__(self, settings=None) -> None:
        self.settings = settings
        self.sr = SAMPLE_RATE
        self._lock = threading.Lock()
        self.backend = None
        self.backend_error: str = ""
        self._cache: dict = {}          # rendered-buffer cache (pre-volume)
        self._cache_order: list = []
        self._closed = False
        self._init_backend()

    # -- backend selection ------------------------------------------------
    def _setting(self, key: str, default):
        if self.settings is None:
            return default
        return self.settings.get(key, default)

    def _init_backend(self) -> None:
        choice = self._setting("audio_backend", "auto")
        soundfont = self._setting("soundfont", "")
        if choice == "fluidsynth":
            # Explicit request: try synchronously so Settings can report failure.
            try:
                from .fluidbackend import FluidBackend

                self.backend = FluidBackend(soundfont=soundfont, sample_rate=self.sr)
                return
            except Exception as exc:  # noqa: BLE001 - fall back gracefully
                self.backend_error = f"{type(exc).__name__}: {exc}"
        self.backend = SynthBackend(self.sr)
        if choice == "auto":
            # Upgrade to the SoundFont backend off the UI thread: the synth is
            # ready instantly, so startup never waits on soundfont loading.
            threading.Thread(target=self._upgrade_to_fluid,
                             args=(soundfont,), daemon=True).start()

    _FLUID_CREATE_LOCK = threading.Lock()   # never load the DLL concurrently

    def _upgrade_to_fluid(self, soundfont: str) -> None:
        try:
            from .fluidbackend import FluidBackend

            with AudioEngine._FLUID_CREATE_LOCK:
                if self._closed:
                    return
                fluid = FluidBackend(soundfont=soundfont, sample_rate=self.sr)
        except Exception as exc:  # noqa: BLE001 - synth keeps working
            self.backend_error = f"{type(exc).__name__}: {exc}"
            return
        adopted = False
        with self._lock:
            if not self._closed and getattr(self.backend, "name", "") == "synth":
                self.backend = fluid
                adopted = True
        if adopted:
            self._cache.clear()  # synth-rendered buffers are stale now
        else:
            fluid.close()        # engine closed (or replaced) while we loaded

    @property
    def backend_name(self) -> str:
        return getattr(self.backend, "name", "none")

    def reload_backend(self) -> None:
        old = self.backend
        self._cache.clear()
        self._cache_order.clear()
        self._init_backend()
        if old is not None and old is not self.backend:
            old.close()

    # -- rendering / playback --------------------------------------------
    _CACHE_MAX = 12

    def render(self, event_list: Sequence[dict], program: Optional[int] = None) -> np.ndarray:
        prog = self._setting("instrument_program", 0) if program is None else program
        key = self._cache_key(event_list, int(prog))
        buf = self._cache.get(key) if key is not None else None
        if buf is None:
            with self._lock:
                buf = self.backend.render(event_list, program=int(prog))
            if key is not None:
                self._cache[key] = buf
                self._cache_order.append(key)
                while len(self._cache_order) > self._CACHE_MAX:
                    self._cache.pop(self._cache_order.pop(0), None)
        vol = float(self._setting("master_volume", 0.8))
        return (buf * max(0.0, min(1.0, vol))).astype(np.float32)

    @staticmethod
    def _cache_key(event_list: Sequence[dict], prog: int):
        """Hashable identity of a render request (replays hit the cache)."""
        try:
            return (prog, tuple(
                (round(float(e["start"]), 4), round(float(e["dur"]), 4),
                 int(e["midi"]), int(e.get("vel", 96)))
                for e in event_list
            ))
        except (KeyError, TypeError, ValueError):
            return None

    def play_events(
        self, event_list: Sequence[dict], program: Optional[int] = None, block: bool = False
    ) -> Optional[np.ndarray]:
        buf = self.render(event_list, program)
        if _sd is None:
            return buf
        device = self._setting("audio_device", -1)
        try:
            self.stop()
            _sd.play(buf, self.sr, device=None if device < 0 else device)
            if block:
                _sd.wait()
        except Exception:  # noqa: BLE001 - never crash the UI on audio errors
            return buf
        return buf

    def stop(self) -> None:
        if _sd is not None:
            try:
                _sd.stop()
            except Exception:  # noqa: BLE001
                pass

    # -- musical conveniences --------------------------------------------
    def play_note(self, midi: int, *, dur: float = 1.0, velocity: int = 96, block: bool = False):
        return self.play_events(
            [{"start": 0.0, "dur": dur, "midi": int(midi), "vel": velocity}], block=block
        )

    def play_interval(
        self, low: int, high: int, *, harmonic: bool = False, tempo: int = 90, block: bool = False
    ):
        if harmonic:
            evs = ev.chord_events([low, high], dur=1.6)
        else:
            evs = ev.melody_events([low, high], tempo_bpm=tempo, beats_per_note=1.0)
        return self.play_events(evs, block=block)

    def play_chord(self, midis: Sequence[int], *, dur: float = 1.8, arpeggiate: bool = False, tempo: int = 90, block: bool = False):
        if arpeggiate:
            evs = ev.melody_events(list(midis), tempo_bpm=tempo, beats_per_note=0.5)
        else:
            evs = ev.chord_events(midis, dur=dur)
        return self.play_events(evs, block=block)

    def play_melody(self, midis: Sequence[int], *, tempo: int = 90, beats_per_note: float = 1.0, block: bool = False):
        return self.play_events(
            ev.melody_events(midis, tempo_bpm=tempo, beats_per_note=beats_per_note), block=block
        )

    def play_sequence(self, items, *, tempo: int = 90, block: bool = False):
        return self.play_events(ev.sequence_events(items, tempo_bpm=tempo), block=block)

    def play_metronome(self, beats: int = 4, *, tempo: int = 90, block: bool = False):
        """Woodblock-ish clicks using high/low pitched short notes."""
        items = []
        for i in range(beats):
            items.append((84 if i == 0 else 76, 1.0))
        return self.play_sequence(items, tempo=tempo, block=block)

    def close(self) -> None:
        self._closed = True
        self.stop()
        with self._lock:
            if self.backend is not None:
                self.backend.close()
