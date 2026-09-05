# Whole-app audit and expansion, September 2026

Baseline: v1.2.0 / 457ada2. This is a source, behavior, curriculum and packaging audit, not a formal penetration test or a claim of exhaustive music pedagogy.

## Coverage and interactions

| Area inspected | Existing behavior | Finding / work selected |
|---|---|---|
| Theory and generators | Spelled notes, intervals, keys, scales, chords, Roman numerals; 54 registered exercise families | Preserve spelling in new transformations; reuse tested generators for worksheets |
| Aural training | Intervals, modes, melody/rhythm/harmony/multipart dictation, cadences, error detection | Rhythm exists in practice but was absent from placement ladder |
| Keyboard | On-screen/MIDI input, scales/chords, pitch sets/rows/P-L-R | No fretted-instrument map; add independently of piano grading |
| SATB | Locked clues, custom harmonies, profiles, bounded/exhaustive search, diagnostics, playback, JSON/MusicXML | Retain scope and honest incomplete-search results; new transposition tool does not claim SATB validity |
| Reference | Circle, explorer, free note analysis, duration calculator, post-tonal workbench, glossary | Reverse scale search and spelled transposition are distinct missing workflows |
| Curriculum | Six levels, III–IV tonal bridge, pregraduate sets/rows, guided advanced topics, Fall 2026 companion | README must distinguish graded activities from guided study |
| Placement | Domain-wide scalar staircase, confirmation, conservative cap | Sparse topic sampling, omitted tonal bridge, fallback items credited at requested difficulty, overconfident copy; improve evidence and coverage |
| Adaptive learning | Elo/BKT estimates, spaced review, prerequisite unlocking, retake preserves progress | Keep real progress intact; present assessment as provisional |
| Progress / engagement | Mastery map, attempts, XP, streaks, achievements, daily goals | Worksheets must not fabricate graded attempts or progress |
| Settings / storage | Local SQLite/Qt settings, JSON export, reset, device/theme/staff controls | New tools remain offline and export only on explicit save |
| Audio / MIDI | Synth fallback, optional SoundFont, device choices, playback and MIDI events | New metronome needs explicit stop and stops on navigation; no microphone claim |
| UI / accessibility | Shared themes, accessible names, staff and keyboard widgets | Test added screens at laptop size; invalidate stale outputs after edits |
| Build / release | Windows onefile + installer, pinned dependencies, source CI, executable self-test | Preserve System32 DLL discovery and no-console streams; test packaged additions |

## External comparison and five selected features

Primary product pages checked September 5, 2026. Listed gaps mean absent from our baseline UI, not that a competitor's complete implementation will be reproduced.

1. **Transposition studio.** [teoria transformations](https://www.teoria.com/en/help/exercises/t.php) covers note-group transposition; [transposing instruments](https://www.teoria.com/en/articles/transposing/04.php) motivates concert/written conversion. Add spelled interval transposition, direction, instrument presets, playback, and MusicXML export.
2. **Reverse scale finder.** [musictheory.net tools](https://www.musictheory.net/tools) provides forward scale calculation; ours already does that. Add the complementary workflow: find candidate scales containing supplied notes, with missing/outside notes and optional tonic. Containment is not a key estimate.
3. **Practice metronome and tap tempo.** The same tools page includes a tempo tapper. Add measured tap tempo, accent grouping, subdivisions, finite practice runs and stop behavior; separate beat units from time-signature denominators.
4. **Custom printable worksheets.** [musictheory.net customization](https://www.musictheory.net/faq) and [EarMaster customized exercises](https://www.earmaster.com/products/ear-training-sight-singing/earmaster-cloud-edition.html) offer focused practice. Add reproducible, selectable written question sets with a separately exported answer key. Do not put audio-only questions on paper or award XP for ungraded work.
5. **Fretboard explorer.** [musictheory.net exercises](https://www.musictheory.net/exercises) includes fretboard notes, intervals, scales and chords. Add a clickable map with guitar/bass/ukulele/custom tuning, pitch-class highlights and note audition. This is an explorer, not automated fingering advice.

At this v1.3 audit, remaining gaps included microphone feedback, imported-score practice, teacher assignments, jazz and score-wide review. **v1.4 adds bounded implementations of these workflows**, described in [Studio expansion](studio-expansion.md). Remaining scope includes cloud collection/class management, human-performance calibration, automatic rhythm alignment, improvisation assessment and comprehensive contrapuntal/harmonic analysis.

## Acceptance scope

- Each of the five tools: independent theory tests, malformed inputs, UI interactions, playback/export where applicable, then regression tests after integration.
- Placement: topic coverage, beginner/advanced/guessing simulations, incomplete-save rejection, generated-item difficulty fidelity, retake preservation, UI results and skip controls.
- README: complete navigation, full generated skill/exercise inventory, guided-vs-graded distinction, settings/data/accessibility, limits and development/release instructions; preserve useful images in a redesigned layout.
- Future expansion skill: repository architecture and fragile invariants, validated skill metadata, locally discoverable copy and committed source.
- Publish tested commits and verify remote state. Record actual outcomes here before completion.

## Verified locally

- Full integrated suite: 462 passed before final display refinements; subsequent targeted regression: 50 passed. Final cross-platform CI includes the two additional assessment guard tests.
- All five utilities have theory tests and interactive Qt checks. Transposition has a MusicXML parse-back test; worksheet question/key exports are checked separately; the metronome's precise event positions, accents, subdivisions and navigation stop are verified; scale containment and fretboard/capo arithmetic have independent examples.
- Placement tests cover high/low response profiles, guessing resistance, demonstrated-difficulty caps, collegiate/rhythm coverage, harder-generation retry evidence, unrelated-fallback rejection, incomplete saves, breadth misses and earned-progress preservation.
- All five Tools pages and initial placement were visually inspected at 1140×740; scrolling verified at 940×620. Corrected white-paper worksheet preview and made sidebar/tool content scrollable.
- README inventory verified against 51 live curriculum skills and 54 registered exercise types; local links resolve. GitHub's Markdown renderer accepted 15 tables and 10 expandable sections. New screenshots show the current tools and placement; earlier demo recordings are explicitly historical.
- Expansion skill passed the skill-creator validator and was installed under the user's local Codex skills directory; the same source is committed in `skills/`.
- Built v1.3.0 Windows portable executable and ran its isolated self-test successfully: Qt screens, five practice tools and exports, existing note/rhythm calculators, SATB, MusicXML and synthesis.
