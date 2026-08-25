# Changelog

All notable changes to Music Theory Master are documented here.
Versioning follows [SemVer](https://semver.org); releases are tagged `vX.Y.Z`
and built automatically by the release workflow.

## [1.0.0] - Unreleased

### Pre-Graduate bridge
- Added a first-class Pre-Graduate level between Advanced and Graduate across
  curriculum ordering, mastery labels, progress maps, and placement ladders.
- Added teach-first paths for 0–11 pitch classes, the chromatic clock, interval
  classes 1–6, normal/prime form, interval-class vectors, Forte tables, Tn/TnI,
  twelve-tone rows/matrices, and neo-Riemannian P/L/R and Tonnetz concepts.
- Added theory, aural, and piano generators for pc conversion/rotation,
  interval-class reasoning and hearing, collection cardinality, P/L/R hearing,
  set realization, ordered row segments, and parsimonious keyboard transforms.
- Added a Post-tonal Reference workbench with a clickable clock, live set
  analyzer, Tn/TnI, audio/keyboard feedback, 12×12 row matrix, and P/L/R path
  player, plus a matching Pre-Graduate tab in the Piano workspace.

### Four-Part Writing Lab
- Added a dedicated offline Part Writing sidebar screen with Create Practice,
  Solve, and Check and Explain workflows over a shared model-backed grid.
- Added an exact deterministic SATB solver, independent final validator,
  structured no-solution diagnostics, targeted auto-correction, cancellable Qt
  worker, top-K navigation, reproducible practice generation, and JSON storage.
- Added named profile-driven rules for chord/inversion/doubling correctness,
  all-pair perfect intervals, tendency tones, melodic writing, cadences,
  cadential six-four, Neapolitan, and augmented-sixth resolution.
- Added Common Practice, Classroom Strict, Species Counterpoint, and locally
  persisted custom profiles with editable severities, weights, and ranges.
- Added SATB-aware chorale, piano, and open-score rendering with four preserved
  voice identities, key/meter/barline/label context, locks, violations, ghost
  answers, and treble/bass/alto/tenor clefs.
- Added full/voice/chord/transition/comparison playback and MusicXML export.
- Added the Advanced `harmony.part_writing` curriculum skill and an offline
  Fall 2026 guide for MUS 2710, MUS 2730, and MUS 2750.

### Staff & notation
- Accidentals are placed from real font metrics: smaller dedicated font, right
  edge a fixed gap left of the notehead, vertically centered on the note's
  line or space. The flat no longer lands on top of the notehead.
- Engraved tilted noteheads with correct stem direction (up below the middle
  line, down above), at a larger default staff size for legibility.
- Optional line/space highlight under each note, optional note-name labels,
  three notehead styles, scaled ledger lines, roomier grand staff.

### Appearance
- Four theme presets: Dark, Light, High Contrast, and Sepia paper, all
  WCAG-AA checked, switchable live from Settings.
- Accent color presets, interface scale control (90%-200%), staff size /
  accidental spacing / paper color controls with a live staff preview, and a
  one-click "Reset to recommended defaults".
- A "reduce motion" toggle that disables celebration animations.

### Engagement
- A bank of hundreds of encouragement messages, written like a musician and
  tied to the concept just practiced, with a no-repeat rotation.
- Confetti celebration overlays for level-ups, skill mastery, and the daily
  goal (each visually distinct, dismissible, under 1.2 s of motion).
- Achievements grown from 11 to 28, plus an Awards gallery screen showing
  locked/unlocked states, unlock dates, and how to earn each one.
- Animated XP / progress bars on the dashboard.

### Distribution
- GitHub Actions CI (Windows + Linux, Python 3.12/3.13, headless GUI tests).
- Tag-triggered release workflow building the portable exe and an Inno Setup
  installer, both with SHA-256 checksums.
- MIT license, contributing guide, security policy, issue/PR templates.

## [0.1.0] - 2026-06-01

- Initial release: adaptive placement, teach-then-drill curriculum across
  theory / aural / piano, Elo+BKT+FSRS mastery model, spaced review, on-screen
  piano and MIDI input, staff dictation, instant synth with background
  FluidSynth upgrade, fully offline with a socket-blocking test guarantee.
