# Contributing to Music Theory Master

Thanks for helping! This project is a PyQt6 desktop app with a strict
offline guarantee and a fully automated test suite. Pull requests are welcome.

## Setup

```powershell
git clone https://github.com/Eipckz/music-theory-master.git
cd music-theory-master
pip install -r requirements.txt -r requirements-dev.txt
python main.py
```

## Before you open a PR

```powershell
python -m pytest tests -q          # must pass (CI runs Windows + Linux)
ruff check music_theory tests      # error-level lint must be clean
```

## Ground rules (enforced by tests)

- **Zero network calls at runtime.** `tests/test_netsafety.py` blocks sockets
  and proves the app still works. Build-time downloads live only in
  `build/fetch_audio_assets.py` and are pinned to SHA-256 hashes.
- **No `eval` / `exec` / `pickle`.** SQL stays parameterized.
- **Every Qt slot wears `@guard(...)`** from `music_theory/errors.py` so an
  exception can never abort the process.
- **Heavy imports stay lazy.** music21 takes ~1 s to import; never import it
  at module top level.

## Adding an exercise type

1. Write a generator `(difficulty: float, rng) -> Exercise` in
   `music_theory/exercises/` and register it with `@register(etype, domain,
   title)`. The parametrized suite auto-covers it: it must self-grade
   (`ex.grade(ex.answer) is True`) at every difficulty and never raise.
2. Add teaching text in `exercises/teaching.py` (shown on wrong answers).
3. If it backs a new curriculum skill: add the `Skill` in
   `curriculum/model.py` **and** lesson pages in `curriculum/lessons.py`.
   `tests/test_lessons.py` fails if any skill lacks a lesson.

## Style

- Match the surrounding code: 4-space indent, type hints, concise docstrings.
- User-facing strings: plain language, no em dashes, no repeated canned lines.
- New settings go in `storage/settings.py` `_SCHEMA` with a default and type.

## Releases (maintainers)

Tag `vX.Y.Z` on master and push the tag. CI builds the exe + installer and
attaches them to a GitHub Release with checksums.
