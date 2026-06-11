# Music Theory Master — developer guide

PyQt6 desktop app (Windows, packaged as a single exe) that teaches music
theory, aural skills, and keyboard skills from beginner to graduate level,
Duolingo-style: adaptive placement → teach-then-drill lessons → spaced review.

## Commands
- Run app: `python main.py`
- Tests: `python -m pytest tests -q` (~2 min; GUI tests run headless via `QT_QPA_PLATFORM=offscreen`, set in conftest)
- Build exe: `./build.ps1` → `dist/MusicTheoryMaster.exe` (PyInstaller onefile; work dir is kept on a local drive because the repo lives in OneDrive)

## Architecture (the 4 layers)
1. **theory/** — pure music math (pitch/Note, scales, chords incl. roman numerals, set theory, twelve-tone, neo-Riemannian). music21 is a *lazy* import (~0.85s) used only for roman numerals/Forte names, with pure-python fallbacks — never import it at module top level.
2. **exercises/** — generators registered via `@register(etype, domain, title)` in `registry.py`. Contract (enforced by parametrized tests in `test_generators.py`): a generator `(difficulty: float 0-10, rng) -> Exercise` must self-grade (`ex.grade(ex.answer) is True`) at every difficulty and never raise; `safe_generate` is the crash-proof wrapper. Teaching text per etype lives in `teaching.py` (shown on wrong answers).
3. **adaptive/** — `placement.py` (2-up/1-down staircase + fast first-miss ramp + confirmation items + cap at twice-demonstrated difficulty; deliberately conservative — never re-tune it to be generous), `mastery.py` (Elo + BKT + FSRS-lite per skill), `scheduler.py` (picks due reviews / new skills / practice).
4. **ui/** — `main_window.py` (sidebar + stacked screens), `exercise_player.py` (renders any Exercise by `InputMode`), `lesson_view.py` (mini-lesson pages), `screens/`. Every Qt slot is wrapped in `@guard(...)` from `errors.py` so an exception can never abort the process — keep that pattern for any new slot.

## Cross-cutting systems
- **Curriculum**: `curriculum/model.py` — skill tree with prereqs, per-skill difficulty bands, placement seeding. `curriculum/lessons.py` — multi-page mini-lessons keyed by skill id; **every skill must have a lesson** (`test_lessons.py` enforces full coverage). New skill = add Skill + generator(s) + teaching text + lesson pages.
- **Audio**: `audio/engine.py` starts on the numpy synth instantly and upgrades to FluidSynth in a background daemon thread ("auto" mode). Buffers are cached (engine-level, keyed by event list) and synth notes are lru_cached. If you touch close/upgrade logic, mind the race: `_closed` flag + `_FLUID_CREATE_LOCK` exist because leaking an unclosed fluid instance hard-crashes (0xC0000409) at GC.
- **Persistence**: `storage/db.py` SQLite in per-user appdata; `kv` table holds flags like `taught.<skill_id>` (lesson shown) and `placement.theta.<domain>`.
- **Startup speed**: `app.warmup_async()` preloads music21 + synth off the UI thread after the window shows. Keep heavy imports lazy.

## Packaging landmines (read music_theory.spec docstring before touching it)
- Never `collect_all('music21')`; never force-import `fluidsynth` in the spec; `torch` must stay excluded or the build deadlocks.

## Testing conventions
- New generators are auto-covered by the parametrized tests — just register them.
- GUI flows are tested headless by driving widgets directly (`_grade`, `_load_next`, `lesson._next()`); see `test_features_gui.py`. First-time skills show a lesson — tests must page through it (`_skip_lesson` helper).
