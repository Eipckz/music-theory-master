# Redesign validation

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

Final current-tree validation: **531 tests passed** (`python -m pytest tests -q`, 186.36 seconds). The repository's error/unused-import lint selection also passed (`python -m ruff check --select E9,F63,F7,F82,F401,F811 music_theory tests build main.py`), and `git diff --check` reported no whitespace errors. An AST comparison found no existing named functions removed from the changed Python files.

New regression coverage includes incomplete scores spanning all chord columns, G2/B2/D3/F3 bass line entry, in-key F-sharp and explicit F-natural entry, rejection of header/opposite-staff clicks, Delete targeting the selected voice, and scale/chord generation for all twelve piano roots. These automated checks supplement the native reviews; they do not replace them.

## Scope and limits

All existing navigation destinations and solver command handlers remain. The theory solver, curriculum, database formats, audio/MIDI configuration, import/export services and previous theme choices were retained. The README removes an older unsupported undo/redo claim rather than promising a feature that does not exist.

Playback controls and notation/readout responses were exercised; acoustic output quality, physical MIDI hardware, microphone capture and every audio backend/device combination were not verified in this session. No claim is made that every exercise was manually completed. Linux rendering and a newly packaged Windows installer were not visually tested. Source publication does not replace previously released binaries.

Remaining nonblocking polish from Generation 4: open-score actions require vertical scrolling at the reviewed 1274×800 window size; layout changes invalidate the displayed solution and require another solve; some neighboring open-score stems are close. These are recorded rather than concealed behind the numerical grade.
