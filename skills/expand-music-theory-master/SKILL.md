---
name: expand-music-theory-master
description: Audit, extend, test and document the Music Theory Master desktop app, including theory engines, assignment tools, curriculum and placement. Use for development of Eipckz/music-theory-master, not for solving a student's assignment in another app.
---

# Expand Music Theory Master

Locate the user's checkout of `Eipckz/music-theory-master` and inspect current branch, status, remote and repository instructions. Read `CLAUDE.md` for architecture and `docs/expansion-audit.md` for prior coverage findings. Treat those findings as historical until checked against current code. Do not assume a remembered release or path is current.

## Choose work from actual gaps

Map the user's requested outcome to the current screens, registered exercise types, curriculum skills and existing tests. For comparisons, use current official product pages and distinguish a missing UI workflow from functionality already available elsewhere in the app. Keep the requested number and scope of additions; do not count a bug fix, tab rename or duplicate calculator as a separate substantial feature. Document remaining gaps honestly.

## Musical and application invariants

- Preserve spelled pitch identity in tonal work; MIDI/pitch-class equivalence is appropriate only when the particular task intentionally ignores spelling or octave. Leading tones and chordal sevenths have different tendencies. Applied dominants depend on local tonic context. Use primary teaching sources to resolve uncertain conventions.
- Keep music calculations in `theory/`; import music21 lazily. Register exercises in `exercises/`, then connect actual lessons, prerequisites and skill IDs when adding curriculum. Generators must self-grade their canonical answer across supported difficulties.
- SATB returns exactly four voices. Preserve locked clues, explicit required tones and user profiles. Report search budgets and incomplete exploration honestly; a bounded failure is not proof of impossibility. Verify final solutions independently of generation.
- Placement must credit the question actually presented. Never label a fallback item as advanced or infer full topic mastery from a tiny sample. Keep incomplete results unsaved and preserve earned progress on retakes. Test high, low and guessing response patterns as well as uneven topic knowledge.
- Qt slots use `errors.guard` or explicit input-error handling. Invalidate outputs and disable playback/export when inputs change. Stop timed audio on navigation. Test screen layouts and keyboard access at the app's supported minimum size as well as normal laptop size.
- Keep runtime offline. Persist user data through existing local storage conventions; importing/exporting exercises must not fabricate graded attempts. Separate printable questions from answers. Preserve theme and accessible-name behavior.
- Studio imports must stay local, bounded and hardened against XML entities/archive expansion. Written pitches and selected timing are distinct from full score performance. Do not claim complete counterpoint analysis from parallel/leap checks.
- Microphone input requires explicit recording, bounded duration and cleanup on navigation. Verify WAV paths and simulated input cleanup without recording ambient audio implicitly. Count missing/unvoiced time as missing evidence and distinguish pitch estimates from vocal-technique assessment.
- Offline assignment files include answer keys: validate nested music/audio payloads, regrade submitted responses against the original file, and never trust a claimed score or fabricate course mastery.

## Validate the actual product

Run focused tests for observable musical behavior and failure cases before integration, then repeat after integration and run the repository's regression/CI gates. Include UI interactions, real export round trips and audio event timing where relevant. Review screenshots rather than relying only on widget construction tests. Enumerate `CURRICULUM` and the exercise registry to keep the README's complete inventory accurate; distinguish guided self-study from automated grading.

Windows packaging is sensitive to DLL discovery. Preserve System32 precedence in `music_theory.spec`, no-console stream initialization in `main.py`, and the isolated frozen-app self-test in `build.ps1`. When changing release content, update the Python version constant, installer default and Windows version resource consistently. Extend `selftest.py` to exercise important new screens/calculations. A successful source launch does not prove the distributed executable works.

## Publish within the current authorization

Stage only reviewed paths. Preserve unrelated user changes. Follow the user's current publishing/release authorization; the skill itself grants none. Verify CI and the remote commit/tag or release assets appropriate to the request. Historical merge commits can make this repository's linear-history rules reject new branch creation: inspect the live rules before choosing a permitted publishing route, and do not weaken protections merely to bypass that error.

For a release, run the published executable's `--self-test <report-path>` in an isolated profile and verify its download checksum. Finish with a requirement-by-requirement audit covering requested features, assessment changes, documentation, tests and remote publication. Do not describe generated questions, source tests or an unpushed branch as a shipped feature.
