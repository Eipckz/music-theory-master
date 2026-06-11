"""User settings persisted as schema-validated JSON.

Security: we only ever read/write a known set of keys with type checks. A
corrupted or hand-edited file degrades gracefully to defaults instead of
executing anything. No eval/exec/pickle is used."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from ..paths import settings_path

# key -> (default, validator)
_SCHEMA: dict[str, tuple[Any, type]] = {
    "audio_backend": ("auto", str),      # auto | fluidsynth | synth
    "soundfont": ("", str),              # absolute path or "" for bundled
    "audio_device": (-1, int),           # sounddevice index, -1 = default
    "midi_input": ("", str),             # device name substring, "" = none
    "master_volume": (0.8, float),
    "instrument_program": (0, int),      # General MIDI program (0 = piano)
    "metronome_enabled": (True, bool),
    "default_tempo": (90, int),
    "theme": ("dark", str),
    "show_note_names": (True, bool),
    "placement_done": (False, bool),
    "name": ("Learner", str),
}


class Settings:
    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = Path(path) if path else settings_path()
        self._data: dict[str, Any] = {k: v[0] for k, v in _SCHEMA.items()}
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError, ValueError):
            return
        if not isinstance(raw, dict):
            return
        for key, (default, typ) in _SCHEMA.items():
            if key in raw and isinstance(raw[key], typ) and not (
                typ is int and isinstance(raw[key], bool)
            ):
                self._data[key] = raw[key]

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        if key not in _SCHEMA:
            return
        default, typ = _SCHEMA[key]
        if typ is float and isinstance(value, int) and not isinstance(value, bool):
            value = float(value)
        if isinstance(value, typ) and not (typ is int and isinstance(value, bool)):
            self._data[key] = value
            self.save()

    def __getitem__(self, key: str) -> Any:
        return self._data[key]
