# Generation 9 — final renewed-cycle native review

Reviewed the running Windows app using Computer Use (`@oai/sky`) at a captured 1274 × 800 window, against `workspace-system-concept.png`. This is the fifth review of the renewed cycle (generations 5–9). No implementation edits were made by this reviewer.

## Scores

| Measure | Score |
|---|---:|
| Visual appearance | 8/10 |
| Adherence to generated reference | 7.5/10 |
| Observed usability | 8.5/10 |

The app now follows the reference structurally: compact icon navigation, editorial headings, task selectors, a main notation/work area, contextual guidance, and reachable primary actions. The tutorial is the closest match and teaches real actions. This is substantially more coherent than the generation-5 baseline. It is not a pixel match: native forms, thinner gray borders, fewer brass accents, text-only module cards, and less sophisticated score engraving remain visible differences.

## Native checks completed

- Studio → Score study → Try a sample score displayed the four-part passage. Play passage and Stop were clicked and remained visible throughout passage-setup scrolling. Audible output was not independently measured.
- Expanded passage setup, scrolled its parts list to Bass, and single-clicked Bass. The preview changed to the bass line alone; this fixes the prior selection problem.
- Inspected Studio Singing, Jazz and Assignments. Task selectors and context guidance worked; main action footers were visible. Singing was inspected without initiating recording or microphone permissions.
- Tools → Transpose showed a two-column setup and persistent action footer, with the result visible. No export was performed.
- Solver: switched open score to Chorale, selected Bass, clicked the staff, and observed `Added C3 · Bass · chord 1`. Solve harmony returned `Solution 1/5 · score 6.00` with a complete four-part score and zero hard-rule violations in the feedback rail. Switching to Piano-style preserved that solution. Stop produced `Playback stopped.`
- Home quick cards and focused Practice question were inspected and captured.
- Tutorial resumed at step 4 with its saved C3 clue and previously removed second note. Continue opened step 5 and showed a ring at F3 with Continue disabled. Pause & leave returned Home; selecting Tutorial resumed the same step and clue.
- Clicking the F3 ring reported `Added F3 · Bass · chord 2`. Solve found five completions; the tutorial explicitly confirmed that C3/F3 clues were preserved and enabled Continue.
- Step 6 kept Continue disabled until Play all was clicked, then displayed `Playback requested` and enabled Continue. Stop remained reachable and worked. This verifies the action gate, not the physical audio output.

## Remaining polish and limits

- At this font scale the 120px parts list displays three rows, so Bass requires an internal scroll. This is usable but four immediately visible SATB rows would be better.
- Studio's introductory paragraph is long; the sample title is below the music and its four attack columns cluster toward the left. A shorter introduction, a title above the score and more even column spacing would improve fidelity.
- Open-score mode needs vertical scrolling at this laptop-sized window. Principal solver actions remain fixed; scrolling is acceptable for the full four-staff view.
- Solver piano is partly below the initial fold at 800px height; direct notation entry and the pinned actions remain available.
- Some secondary modules still have large text/result panels and generic numbered selectors. They are clearer, but do not yet equal the concept's handcrafted detail.
- Did not resize to the absolute minimum window, retest first-launch routing, complete every exercise type, record audio, connect MIDI hardware, export/import every format, or validate physical sound output. Those claims must not be inferred from this review.

## Captures

`current-home.png`, `current-solver.png`, `current-studio.png`, `current-tutorial.png`, and `current-practice.png` were saved directly from native screenshots. The tutorial capture shows the F3 target and disabled Continue before the required action.

The implementation owner plans a small final Studio polish pass after this review. These scores describe the version inspected here, not unseen later changes.
