# Changelog

All notable changes to Music Theory Master are documented here.
Versioning follows [SemVer](https://semver.org); releases are tagged `vX.Y.Z`
and built automatically by the release workflow.

## [1.0.0] - Unreleased

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
