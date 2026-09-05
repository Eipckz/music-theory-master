# Music Theory Master — developer guide

PyQt6 desktop app (Windows, packaged as a single exe) that teaches music
theory, aural skills, and keyboard skills from beginner to graduate level,
Duolingo-style: adaptive placement → teach-then-drill lessons → spaced review.

## Commands
- Run app: `python main.py`
- Tests: `python -m pytest tests -q` (~2.5 min; GUI tests run headless via `QT_QPA_PLATFORM=offscreen`, set in conftest; conftest also pins the test profile to the synth backend because FluidSynth's native teardown is the known 0xC0000409-at-exit flake)
- Lint (same gate as CI): `ruff check --select E9,F63,F7,F82,F401,F811 music_theory tests build main.py`
- Build exe: `./build.ps1` → `dist/MusicTheoryMaster.exe` (PyInstaller onefile; work dir is kept on a local drive because the repo lives in OneDrive)
- Staff rendering previews: `python build/render_staff_preview.py` → PNGs in `build/staff_preview/` (uses the real QPA + WA_DontShowOnScreen — offscreen has no fonts on Windows)
- Release: tag `vX.Y.Z` and push → `.github/workflows/release.yml` builds the exe + Inno Setup installer and attaches both (with .sha256) to a GitHub Release

## Architecture (the 4 layers)

### v1.4 musicianship studio
- `theory/score_study.py` imports bounded local MusicXML/MXL with hardened XML parsing, retains written pitch and timing, selects passages and reviews independent monophonic lines. Do not imply universal counterpoint validity or full notation playback.
- `audio/pitch_tracking.py` analyzes single-voice WAV/captured samples; `audio/recording.py` opens an input stream only after an explicit Record action. Close it on navigation. Missing/unvoiced recording time is missing evidence, never a successful note.
- `theory/jazz.py`, `exercises/jazz_gen.py` and five curriculum lessons connect ii–V–I, guides, substitutions, listening and keyboard work. Preserve enharmonic spelling while explaining pitch-class equivalence.
- `exercises/assignments.py` defines bounded offline assignment/result exchange. Regrade responses against the original assignment; do not trust claimed scores or import attempts into course progress. Files contain the answer key and do not establish identity.
- `ui/screens/studio.py` connects the four tabs, background pitch analysis and shared exercise player. Clear pending results on edits and close audio on navigation. Keep controls usable at 940×620.
- Focused tests: `test_score_study.py`, `test_pitch_tracking.py`, `test_jazz.py`, `test_assignments.py`, `test_studio_gui.py`; packaged `selftest.py` also imports scores, reads WAV and regrades assignment files.

### v1.3 practice tools and assessment
- `theory/practice_tools.py` holds transposition, reverse scale search, metronome events/tap tempo, fretboard and worksheet calculations; `ui/screens/practice_tools.py` exposes all five under Tools.
- Placement's UI enables comprehensive breadth checks by default; the core API retains a short-mode default for compatibility. Results are provisional and retain per-item type/difficulty evidence. Never substitute an unrelated fallback or save an incomplete assessment.
- `skills/expand-music-theory-master/SKILL.md` is the reusable development skill; `docs/expansion-audit.md` records the comparison and verification scope. README's full curriculum and generator inventory must match the live registry.

1. **theory/** — pure music math (pitch/Note, scales, chords incl. roman numerals, set theory, twelve-tone, neo-Riemannian). music21 is a *lazy* import (~0.85s) used only for roman numerals/Forte names, with pure-python fallbacks — never import it at module top level.
2. **exercises/** — generators registered via `@register(etype, domain, title)` in `registry.py`. Contract (enforced by parametrized tests in `test_generators.py`): a generator `(difficulty: float 0-10, rng) -> Exercise` must self-grade (`ex.grade(ex.answer) is True`) at every difficulty and never raise; `safe_generate` is the crash-proof wrapper. Teaching text per etype lives in `teaching.py` (shown on wrong answers).
3. **adaptive/** — `placement.py` (2-up/1-down staircase + fast first-miss ramp + confirmation items + cap at twice-demonstrated difficulty; deliberately conservative — never re-tune it to be generous), `mastery.py` (Elo + BKT + FSRS-lite per skill), `scheduler.py` (picks due reviews / new skills / practice).
4. **ui/** — `main_window.py` (sidebar + stacked screens + the `celebrate()` overlay), `exercise_player.py` (renders any Exercise by `InputMode`), `lesson_view.py` (mini-lesson pages), `screens/` (incl. `reference.py` = circle of fifths / explorer / post-tonal workbench / glossary, `achievements.py` = awards gallery). Every Qt slot is wrapped in `@guard(...)` from `errors.py` so an exception can never abort the process — keep that pattern for any new slot.

### Pre-Graduate bridge
- `LEVEL_ORDER` is Beginner → Early → Intermediate → Advanced → Pre-Graduate → Graduate. Keep the matching tuple in `feedback_messages.py` and thresholds in `adaptive/mastery.py` synchronized.
- The theory path is representational before analytical: `posttonal.pitch_classes` → interval classes / normal form → prime form / vectors → Forte / Tn/TnI → rows and matrices. Aural and piano skills deliberately depend on those written concepts and add real listening/keyboard work.
- Pure calculations and parsing live in `theory/settheory.py`, `twelvetone.py`, and `neoriemann.py`; generators live in `exercises/pregraduate_gen.py` and `posttonal_gen.py`; lesson pages live in `curriculum/lessons.py`.
- Interactive support lives in Reference → Post-tonal bridge (`PitchClassClockWidget`, set analyzer, matrix, P/L/R path) and Piano → Pre-Graduate. Preserve the distinction between key-relative scale degree and fixed pc number, and between twelve-tone P/I/R/RI and neo-Riemannian P/L/R.
- Focused verification: `python -m pytest tests/test_pregraduate.py tests/test_theory.py tests/test_generators.py tests/test_lessons.py tests/test_reference.py tests/test_engagement.py -q`.

### Four-Part Writing Lab
- Pure engine: `theory/part_writing/` (models → normalization/profiles/rules → cached voicing enumeration → layered solver → diagnostics/generator/serialization/export). Qt must never enter this package; music21 stays lazy and is not the rule authority.
- UI: `ui/screens/part_writing.py` and `ui/widgets/satb_staff.py`. `PartWritingTableModel` owns the editable progression. Every hard constraint is honored or reported; never silently relax locks.
- Correctness is profile-relative. Do not claim universal textbook agreement. Parallel fourths are allowed by Common Practice and independently configurable.
- Focused verification: `python -m pytest tests/test_part_writing_models.py tests/test_part_writing_rules.py tests/test_part_writing_solver.py tests/test_part_writing_generator.py tests/test_part_writing_diagnostics.py tests/test_part_writing_serialization.py tests/test_part_writing_gui.py tests/test_part_writing_export.py -q`.
- Developer extension guide: `.claude/skills/part-writing/SKILL.md`.

## Theming & staff appearance
- `ui/theme.py`: 4 palettes (dark / light / high_contrast / sepia) + accent presets. `apply_theme(app, settings)` switches live by mutating module attributes — **read colors as `theme.ACCENT` (module attribute access), never `from .theme import ACCENT`**, which freezes the import-time value. All palettes + accent combos are WCAG-AA checked by `tests/test_appearance.py`.
- `ui/widgets/staff.py`: the engraving. Metrics-placed accidentals, chord columns with accidental lanes (`set_columns(columns, durations=, ghost=)`), whole/half/quarter heads, `set_meter()` + barlines. User appearance flows settings → `configure_staff_appearance()` → module-level `STYLE` dict; per-widget `line_spacing` assignment still overrides. Verify visual changes with `build/render_staff_preview.py`, not by reading code.

## Engagement systems
- `feedback_messages.py`: 768-message bank keyed (domain, level, event) with a kv-backed no-repeat rotation (`pick_message(db, domain, level, event, **fmt)`). House style: name the concept being celebrated, no em dashes, no hype words — `tests/test_engagement.py` enforces coverage and style.
- `achievements.py`: `ACHIEVEMENTS` = key → (title, description); evaluation is idempotent and computed purely from existing tables (no new storage). The Awards screen shows all with locked/unlocked states.
- `ui/celebration.py`: confetti overlay + `animate_bar`; respects the `reduce_motion` setting and must stay cosmetic-only (entry points guarded, never raise into session flow).

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
