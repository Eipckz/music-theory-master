"""Filesystem locations for app data and bundled resources.

User state lives under %APPDATA%\\MusicTheoryMaster on Windows (mirrors the
SpeedReader convention). Read-only resources ship inside the package and are
located in a PyInstaller-aware way."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from . import __app_id__


def is_frozen() -> bool:
    """True when running from a PyInstaller bundle."""
    return getattr(sys, "frozen", False)


def resource_root() -> Path:
    """Directory that contains bundled, read-only resources.

    When frozen, PyInstaller extracts datas under sys._MEIPASS. In source
    runs it is the package directory."""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent


def resources_dir() -> Path:
    """Locate the bundled resources folder across source and frozen layouts."""
    root = resource_root()
    candidates = [
        root / "resources",                    # source run (package dir)
        root / "music_theory" / "resources",   # frozen, datas under package path
    ]
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]


def soundfonts_dir() -> Path:
    return resources_dir() / "soundfonts"


def fluidsynth_bin_dir() -> Path:
    return resources_dir() / "fluidsynth"


def app_data_dir() -> Path:
    """Per-user writable directory for settings + the progress database."""
    base = os.environ.get("APPDATA")
    if not base:
        base = str(Path.home() / ".config")
    d = Path(base) / __app_id__
    d.mkdir(parents=True, exist_ok=True)
    return d


def settings_path() -> Path:
    return app_data_dir() / "settings.json"


def database_path() -> Path:
    return app_data_dir() / "library.db"


def log_path() -> Path:
    return app_data_dir() / "mtm.log"
