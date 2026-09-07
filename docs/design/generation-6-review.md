# Generation 6 — native review

Reviewed the running PyQt application at approximately 1274 × 800 on Windows, compared directly with `workspace-system-concept.png`. This review covers the running build before the concurrently prepared compact-sidebar and layout fixes. No implementation files were edited.

Scores: **appearance 6/10**, **reference adherence 5/10**, **usability 6/10 overall; hands-on tutorial 8/10**. Do not treat the tutorial score as whole-app certification.

## Human interaction evidence

- Continued the tutorial after the actual C3 entry in step 2; placed F3 on the indicated bass line in chord 2. Continue stayed disabled until the expected action was performed.
- Right-clicked chord 2 to remove its bass note; observed success, restored F3, and pressed Solve harmony. The UI returned solution 1/5, rendered all voices, and allowed progression.
- Pressed Play all; the tutorial recognized the playback request. This verifies the interaction, not audible speaker output.
- Opened Assignment; the table showed C3 and F3 as the bass clues, with other clue voices empty. Finished the tutorial and observed the completed/replay state.
- Opened Piano and clicked C2: readout showed C2 / MIDI 36; the staff changed to bass clef and showed the expected low ledger position.
- Opened Reference and clicked G major: relative E minor and one-sharp F signature appeared.
- Inspected Studio, Practice, Tools/Transpose, Tools/Find scales and main Part Writing through native navigation. No microphone, MIDI hardware, or imported-score workflow was exercised.

## Must fix

1. **Practice layout overlaps itself.** Domain cards sit across the header at the top of the window. Topic and difficulty controls overwrite the title/description. The question remains visible but the workspace is not shippable at this size. Evidence: `generation-6-practice.png`.
2. **Studio remains a form rather than a score workspace.** Its Parts list forces the left field column to take approximately 80% of the width. Measure and tempo inputs become huge, while voice and first-measure fields are tiny. All six actions are equally secondary; Open MusicXML has no primary emphasis. There is no example score or helpful empty-state illustration. Evidence: `generation-6-studio.png`.
3. **Sidebar and score sizing still waste vertical space.** Brand wraps into three lines, sidebar preferences are below the fold, normal solver piano is entirely below the viewport, tutorial piano only appears as a thin slice. Main process is already preparing fixes, but this running build still demonstrates the issue.
4. **Tutorial context is overwritten by module changes.** Opening Assignment replaces the tutorial step kicker with ASSIGNMENT, losing 7/7 context. Suppress normal coach module updates in tutorial mode.

## Detail refinements

- Fix literal ampersands in button labels: native buttons show Practice rules, Listen files, Pause leave and Practice Dictation, while explanatory copy uses the intended ampersands.
- Match module-help keys to actual Tools labels: Transpose and Find scales currently receive generic tool guidance instead of contextual instructions.
- The large treble/bass glyphs dominate the score and look less typeset than the reference. Bass F dots are correctly aligned; review glyph proportions without changing pitch geometry.
- Reference and Piano are the most convincing normal modules: clear canvas, consistent editorial header, useful coach. Part Writing now has substantially better structural hierarchy and pinned Solve/Check/Play controls.
- Tutorial completion exposes both Replay first harmony and Restart tutorial, which seem redundant without explaining the difference. Consider one clear restart action.
- The concept includes task-card icons/subtitles, gold accents, precise bordered canvas grouping, and a progress checklist. The implementation still has text-only module cards, mostly flat green surfaces, broad empty panels and no tutorial step overview. These are optional refinements after the blocker fixes, but they explain the remaining reference gap.

## Evidence

- `generation-6-tutorial.png`: real Assignment gate, C3/F3 clues, enabled Finish.
- `generation-6-practice.png`: overlapping controls/header.
- `generation-6-studio.png`: field imbalance and equal action weighting.
- `generation-6-solver.png`: pinned actions, guidance rail, obscured lower score/piano at this size.

Native UI control released back to the main agent after this review.
