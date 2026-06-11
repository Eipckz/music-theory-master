"""Security: the shipped package must be fully offline and free of dangerous
dynamic-execution primitives. We both scan the source and prove the runtime
works with networking disabled."""

from __future__ import annotations

import random
import re
import socket
from pathlib import Path

import pytest

import music_theory

PKG_ROOT = Path(music_theory.__file__).resolve().parent

# import-of-forbidden-module and dangerous calls
_FORBIDDEN_IMPORT = re.compile(
    r"^\s*(?:import|from)\s+(socket|urllib|http|requests|ftplib|smtplib|"
    r"telnetlib|asyncio|aiohttp|subprocess|pickle|shelve|marshal)\b",
    re.MULTILINE,
)
_FORBIDDEN_CALL = re.compile(r"(?<![\w.])(eval|exec)\s*\(")


def _py_files():
    return [p for p in PKG_ROOT.rglob("*.py")]


def test_no_forbidden_imports_in_package():
    offenders = []
    for path in _py_files():
        text = path.read_text(encoding="utf-8")
        if _FORBIDDEN_IMPORT.search(text):
            offenders.append(path.name)
    assert not offenders, f"forbidden network/serialization imports in: {offenders}"


def test_no_eval_exec_calls():
    offenders = []
    for path in _py_files():
        text = path.read_text(encoding="utf-8")
        # ignore app.exec() (Qt event loop) which is attribute access, not bare exec(
        for m in _FORBIDDEN_CALL.finditer(text):
            offenders.append((path.name, m.group(0)))
    assert not offenders, f"eval/exec found: {offenders}"


def test_runtime_works_without_network(monkeypatch, tmp_path):
    def _blocked(*_a, **_k):
        raise OSError("network access is blocked in tests")

    monkeypatch.setattr(socket, "socket", _blocked)
    monkeypatch.setattr(socket, "create_connection", _blocked)

    # sanity: networking really is blocked now
    with pytest.raises(OSError):
        socket.socket()

    # exercise generation
    from music_theory.exercises.registry import all_types, generate
    for etype in all_types()[:8]:
        ex = generate(etype, 5.0, random.Random(0))
        assert ex.grade(ex.answer)

    # audio rendering
    from music_theory.audio.engine import AudioEngine
    from music_theory.audio import events as ev
    from music_theory.storage import Settings
    s = Settings(tmp_path / "s.json")
    s.set("audio_backend", "synth")
    eng = AudioEngine(s)
    assert eng.render(ev.melody_events([60, 62, 64])).size > 0
    eng.close()

    # storage
    from music_theory.storage import Database
    d = Database(tmp_path / "n.db")
    d.add_xp(10)
    assert d.get_profile()["total_xp"] == 10
    d.close()
