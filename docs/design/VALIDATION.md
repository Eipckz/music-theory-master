# Redesign validation

## Second design cycle

Following user feedback, the first design was compared more strictly with its generated reference. The renewed cycle uses `work/qa-profile-v2`, leaving the user's normal application data separate. Each reviewer is a dedicated subagent named one generation higher. These are independent judgments, not an averaged product score.

| Reviewer | Appearance | Reference match | Usability | Evidence |
|---|---:|---:|---:|---|
| Generation 5 | 5/10 | 3/10 | Not regraded | [Reference audit](generation-5-review.md); identified the structural gap. |
| Generation 6 | 6/10 | 5/10 | 6/10 | [Native review](generation-6-review.md); full tutorial 8/10, Practice layout regression and Studio imbalance found. |
| Generation 7 | 7/10 | 6/10 | 8/10 | [Native review](generation-7-review.md); Practice fixed, tutorial replay and sample score functional, Studio score below fold. |
| Generation 8 | 7.5/10 | 7/10 | 8/10 | [Native review](generation-8-review.md); score-first Studio, tutorial 8.5/10; action footer needed pinning. |
| Generation 9 | 8/10 | 7.5/10 | 8.5/10 | [Final native review](generation-9-review.md); pinned controls, Bass isolation, retained solutions and tutorial action gates verified. |

Second-cycle local regression validation: **535 tests passed** (187.04 seconds), with 14 focused Studio/tutorial/tool tests and five solver GUI tests repeated after follow-up changes. Error/unused-import lint passed. The four added tests cover tutorial isolation/gates/resume/completion and grouped score-preview selection; an existing solver test now also verifies layout changes retain solutions. GitHub CI and release builds run the full suite against the published revision.

### Changes driven by the renewed reviews

- Shared editorial headers, module cards, contextual guidance rails and compact icon navigation replace the palette-only approach.
- Solver task cards separate Write, Assignment, Practice & rules and Listen & files. Solve/Stop/Check/Play remain outside the scroll area; diagnostics sit beside the score.
- Nested Qt layouts are explicitly reparented during workspace composition, resolving the Practice overlap caught in Generation 6.
- Studio/Tools fields use balanced columns. Their action footers stay outside the scrolling task body. Studio score study shows the pitch overview before a collapsible setup panel, with a bundled original example score.
- Tutorial runs the real editor against an isolated score store. The reviewer completed Bass selection, C3, F3, removal, re-entry, real solving, playback request and Assignment inspection. Replay was also exercised. Unit checks separately protect the real assignment autosave, wrong-pitch gates, resume and completion persistence.
- The tutorial's step indicator stays stable across task switches. Completion feedback names the action just accomplished. First launch can be skipped; Pause, Resume, Restart and Replay remain accessible.
- Clefs were reduced in size while retaining their staff anchors. Display-layout changes preserve solutions. Stop now stops playback as well as cancelling a search.

### Scope of the current visual evidence

Native screenshots are captured using Windows Computer Use, not a rendered mockup or headless screenshot harness. The generated four-workspace board is explicitly labeled a concept. Studio's canvas is a bounded pitch overview at selected attack times, not full score engraving. Expanded settings and tall/open scores can require scrolling; principal action footers remain reachable.

The earlier-cycle record below is retained as history. Its more optimistic appearance scores preceded the user's stricter reference-match feedback and should not be compared as if they used the same criteria.

After Generation 9, the main agent shortened Studio's introduction, displayed the loaded score title, spread simultaneous attack columns across the canvas, added bottom clearance for bass stems, and expanded the parts list to show the four sample parts. Native follow-up confirmed the new canvas, all four parts and the persistent footer; `current-studio.png` records this follow-up. Field cells align labels/controls at the top of mixed-height rows. The sidebar mark is also rendered into the Windows icon by the build script. Version metadata is synchronized at 1.5.0 for release packaging.

## First design cycle (historical)

The app was launched from this checkout with a separate `APPDATA` profile under the task's `work/qa-profile` directory. Native reviews used Windows Computer Use (`@oai/sky`), actual screenshots, pointer clicks and keyboard input. The user's normal progress database was not used for QA.

## Independent review rounds

| Reviewer | Appearance | Observed usability | Evidence |
|---|---:|---:|---|
| Generation 1 | 7/10 | 6/10 | [Review](generation-1-review.md): first score-first layout; found clef/meter overlap and generic feedback. |
| Generation 2 | 8/10 | 8/10 | [Review](generation-2-review.md): successful solve, C3/F3 entry, removal, piano entry; found Home contrast and bass-dot placement issues. |
| Generation 3 | 8.5/10 | 8.5/10 | [Review](generation-3-review.md): corrected Home/clef, native JSON roundtrip and MusicXML export. |
| Generation 4 | 8.5/10 | 8.5/10 | [Review](generation-4-review.md): corrected C/D piano scales and chord, C2 bass preview, final Chorale/Open score solving. |

Scores are reviewer judgments, not a claim of exhaustive product certification. Each review states exactly what it exercised and what it did not.

## Observed native workflows

- Home navigation and learning/solver entry points render with readable actions.
- Solver Reset → Solve produces five ranked solutions for I–IV–V–I.
- Bass entry places C3 and F3 in separate chord columns, immediately showing partial notes while leaving unknown voices blank.
- Right-click removes only the selected voice's note; a piano key can re-enter it into the selected cell.
- Bass-clef dots straddle the F3 line; time/key signatures have independent space and do not change the next clef's font.
- JSON Save/Open preserves supplied C3/F3 bass clues and unknown remaining voices. Solved MusicXML export produced a score-partwise document. QA files are local scratch data, not shipped assets.
- Home, Learn, Reference, Studio, Placement and Piano were inspected through the actual application. The dedicated Piano check exposed the original C-root scale error; natural-root specifications were corrected for all seven natural roots.
- Main-agent follow-up switched Chorale → Open score → Chorale through the native combo/keyboard and verified the piano disclosure collapses with Space after focus. Final label spacing was adjusted to keep bass stems and open-score voice labels clear of other notation.

### Computer-control calibration

The Windows runtime's captured frame and input origin differed by 8 pixels vertically on this desktop. Generation 2 compensated the tool coordinates and confirmed correct visual staff positions: C3 and F3 landed in the expected space and line. The app's pitch mapping was **not** shifted to compensate for the tool. Regression tests independently verify widget-local bass-line entry for every chord column.

## Regression coverage

First-cycle validation: **531 tests passed** (`python -m pytest tests -q`, 186.36 seconds). The repository's error/unused-import lint selection also passed (`python -m ruff check --select E9,F63,F7,F82,F401,F811 music_theory tests build main.py`), and `git diff --check` reported no whitespace errors.

New regression coverage includes incomplete scores spanning all chord columns, G2/B2/D3/F3 bass line entry, in-key F-sharp and explicit F-natural entry, rejection of header/opposite-staff clicks, Delete targeting the selected voice, and scale/chord generation for all twelve piano roots. These automated checks supplement the native reviews; they do not replace them.

## Scope and limits

All existing navigation destinations and solver command handlers remain. The theory solver, curriculum, database formats, audio/MIDI configuration, import/export services and previous theme choices were retained. The README removes an older unsupported undo/redo claim rather than promising a feature that does not exist.

Playback controls and notation/readout responses were exercised; acoustic output quality, physical MIDI hardware, microphone capture and every audio backend/device combination were not verified in this session. No claim is made that every exercise was manually completed. Linux rendering and a newly packaged Windows installer were not visually tested. Source publication does not replace previously released binaries.

Historical Generation 4 findings included scrolling to open-score actions, layout switches discarding results, and close neighboring stems. The second cycle pins the action row and preserves results across layout switches; tall notation itself still scrolls.
