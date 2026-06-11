"""Shared pytest fixtures and environment isolation."""

from __future__ import annotations

import os
import tempfile

# Isolate user-state and force headless Qt *before* the package is imported.
_TMP_APPDATA = tempfile.mkdtemp(prefix="mtm_tests_")
os.environ["APPDATA"] = _TMP_APPDATA
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from music_theory.errors import install_excepthook
from music_theory.storage import Database, Settings

# Pin the default test profile to the pure-python synth. The FluidSynth
# backend loads in a background thread and its native teardown can crash at
# process exit; tests that target FluidSynth explicitly still construct it
# with their own settings.
Settings().set("audio_backend", "synth")

# PyQt6 calls qFatal() (process abort, 0xC0000409 on Windows) when a Python
# exception escapes a slot or virtual *and* sys.excepthook is the default.
# The app installs this hook in main(); tests must match, so a stray slot
# exception surfaces as a logged traceback instead of killing the whole run.
install_excepthook()


@pytest.fixture
def db(tmp_path):
    d = Database(tmp_path / "test.db")
    yield d
    d.close()


@pytest.fixture
def settings(tmp_path):
    return Settings(tmp_path / "settings.json")
