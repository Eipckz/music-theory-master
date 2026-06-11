"""SoundFont synthesis via fluidsynth, rendered offline to a numpy buffer.

The installed `pyfluidsynth` hard-codes ``os.add_dll_directory('C:\\tools\\
fluidsynth\\bin')`` at import and raises if that path is absent. We neutralize
that by temporarily wrapping ``os.add_dll_directory`` so a missing directory is
ignored, while making our *vendored* DLL directory discoverable via PATH (which
is what ``ctypes.util.find_library`` actually searches on Windows).

If anything here fails, the caller falls back to the numpy synth - audio is
never lost."""

from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Optional, Sequence

import numpy as np

from ..paths import fluidsynth_bin_dir, soundfonts_dir

SAMPLE_RATE = 44100
_RELEASE_SECONDS = 0.5


def _safe_import_fluidsynth(vendored_bin: Path):
    """Import the fluidsynth module with the DLL path landmines defused."""
    orig = getattr(os, "add_dll_directory", None)

    if vendored_bin.exists():
        os.environ["PATH"] = str(vendored_bin) + os.pathsep + os.environ.get("PATH", "")

    if orig is not None:
        def _safe(path):
            try:
                return orig(path)
            except (FileNotFoundError, OSError):
                return None

        os.add_dll_directory = _safe  # type: ignore[assignment]
        if vendored_bin.exists():
            try:
                orig(str(vendored_bin))
            except OSError:
                pass
    try:
        import fluidsynth  # noqa: WPS433 (deferred import is intentional)

        return fluidsynth
    finally:
        if orig is not None:
            os.add_dll_directory = orig  # type: ignore[assignment]


def find_soundfont(preferred: str = "") -> Optional[Path]:
    if preferred:
        p = Path(preferred)
        if p.is_file() and p.suffix.lower() in (".sf2", ".sf3"):
            return p
    d = soundfonts_dir()
    if d.exists():
        for ext in ("*.sf2", "*.sf3"):
            hits = sorted(d.glob(ext))
            if hits:
                return hits[0]
    return None


class FluidBackend:
    name = "fluidsynth"
    available = False

    def __init__(self, soundfont: str = "", sample_rate: int = SAMPLE_RATE) -> None:
        self.sr = sample_rate
        self._lock = threading.Lock()
        self._fl = _safe_import_fluidsynth(fluidsynth_bin_dir())
        sf = find_soundfont(soundfont)
        if sf is None:
            raise RuntimeError("No SoundFont (.sf2) found.")
        self.soundfont_path = sf
        self.synth = self._fl.Synth(gain=0.6, samplerate=float(sample_rate))
        self.sfid = self.synth.sfload(str(sf))
        if self.sfid == -1:
            raise RuntimeError(f"fluidsynth failed to load SoundFont: {sf}")
        self.synth.program_select(0, self.sfid, 0, 0)
        self.available = True

    def render(self, events: Sequence[dict], program: int = 0) -> np.ndarray:
        if not events:
            return np.zeros((1, 2), dtype=np.float32)
        sr = self.sr
        release = int(_RELEASE_SECONDS * sr)
        actions: list[tuple[int, int, int, int]] = []
        for ev in events:
            on = max(0, int(ev["start"] * sr))
            off = max(on + 1, int((ev["start"] + ev["dur"]) * sr))
            vel = max(1, min(127, int(ev.get("vel", 96))))
            midi = int(ev["midi"])
            if 0 <= midi <= 127:
                actions.append((on, 1, midi, vel))
                actions.append((off, 0, midi, 0))
        if not actions:
            return np.zeros((1, 2), dtype=np.float32)
        actions.sort(key=lambda a: (a[0], a[1]))
        end = max(a[0] for a in actions) + release

        with self._lock:
            self.synth.program_select(0, self.sfid, 0, max(0, min(127, int(program))))
            chunks: list[np.ndarray] = []
            pos = 0
            i = 0
            n = len(actions)
            while pos < end:
                nxt = min(actions[i][0], end) if i < n else end
                if nxt > pos:
                    chunks.append(self.synth.get_samples(nxt - pos))
                    pos = nxt
                while i < n and actions[i][0] <= pos:
                    _, kind, midi, vel = actions[i]
                    if kind == 1:
                        self.synth.noteon(0, midi, vel)
                    else:
                        self.synth.noteoff(0, midi)
                    i += 1
            # ensure nothing is left ringing for the next render
            for _, kind, midi, _vel in actions:
                if kind == 1:
                    self.synth.noteoff(0, midi)

        if not chunks:
            return np.zeros((1, 2), dtype=np.float32)
        raw = np.concatenate(chunks).astype(np.float32) / 32768.0
        if raw.size % 2:
            raw = raw[:-1]
        stereo = raw.reshape(-1, 2)
        peak = float(np.max(np.abs(stereo))) if stereo.size else 0.0
        if peak > 0.99:
            stereo *= 0.99 / peak
        return stereo

    def close(self) -> None:
        try:
            with self._lock:
                self.synth.delete()
        except Exception:  # noqa: BLE001 - cleanup must never raise
            pass
