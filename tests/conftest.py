"""Shared pytest fixtures and environment isolation."""

from __future__ import annotations

import os
import tempfile

# Isolate user-state and force headless Qt *before* the package is imported.
_TMP_APPDATA = tempfile.mkdtemp(prefix="mtm_tests_")
os.environ["APPDATA"] = _TMP_APPDATA
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from music_theory.storage import Database, Settings


@pytest.fixture
def db(tmp_path):
    d = Database(tmp_path / "test.db")
    yield d
    d.close()


@pytest.fixture
def settings(tmp_path):
    return Settings(tmp_path / "settings.json")
