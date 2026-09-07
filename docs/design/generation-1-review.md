# Generation 1 design and usability review

Reviewed the live native Music Theory Master window through the Windows Computer Use skill and `@oai/sky`, using fresh screenshots and real clicks. This is a bounded human-path review, not an automated-test result. The running build predates some newer source changes, including the reported clef/meter spacing fix.

**Appearance: 7/10. Functionality/usability observed: 6/10.** These grades apply to the inspected solver workflow, not every app feature.

## What worked

- The dark green shell, cream notation surface, mint voice selection, and serif heading establish a coherent, calmer visual identity. They clearly reference the generated Modern Conservatory concept.
- Part Writing is easy to find in persistent navigation. Choosing Bass changes both the highlighted button and the instruction to identify the lower staff.
- Clicking the staff places notes in distinct chord columns; the status identifies the actual pitch, voice, and chord number.
- Solving inconsistent input promptly shows a failure status and colors the offending notes red. The entered A2 on I and E3 on IV do conflict with the default C-major harmony.
- The assignment table and optional piano both expand through clear disclosure controls. Scrolling exposes the retained slot-editing controls.

## Highest-priority follow-up

1. **Calibrate staff click coordinates before changing pitch mathematics.** Two Computer Use clicks produced notes one diatonic position below the visible target. The screenshot was 1274 by 800, with returned originX=9 and originY=0. Before scrolling, bass lines appeared at y=463,478,493,508,523. Clicking (443,508), on the B2 line, produced `Added A2 · Bass · chord 1`, with the notehead near y=516. Clicking (664,478), on the F3 line, produced `Added E3 · Bass · chord 2`, with the notehead near y=486. The consistent ~8-pixel offset could be window-frame/input-coordinate behavior rather than app pitch mapping. Independently verify with a calibrated pointer or mouse-event positions; do not blindly shift musical mapping.
2. **Make failed solving actionable.** `Input constraints conflict. Visited 0 nodes in 0.00s.` is technically informative but does not tell a learner what to fix. Identify the chord, voice, incompatible pitch and allowed chord tones; keep search metrics secondary.
3. **Finish notation polish.** The live build's bass-clef dots and 4/4 overlap; the parent reports a source fix already exists, so recheck after restart. Roman numerals and chord numbers are small compared with the empty notation space. Increase their readability and show a subtle selected-column cue.
4. **Clarify primary versus secondary actions.** Solve harmony and Check currently have equal mint emphasis, while Stop remains visible at idle. Give Solve a clear primary role and communicate inactive playback/search states.
5. **Close the gap to the brand reference.** Colors and typography are present, but the plain `M / M` text identity and text-only navigation omit much of the concept's recognizable monogram, gold accents and restrained line iconography. A compact next-step/feedback card could provide the coaching the reference promises without crowding the staff.

## Interaction and coverage limits

Navigated to Part Writing; selected Bass; clicked notes in chords 1 and 2; invoked Solve harmony; expanded the assignment table; scrolled; expanded the piano. The conflicting-input response was verified, but a successful solve and piano-key input were not verified in this bounded pass. No claim is made about playback audio, all feature parity, other pages, or final production readiness.

## Screenshot evidence

- [Initial solver](generation-1-empty-solver.png)
- [Bass entry and returned pitch](generation-1-bass-entry.png)
- [Expanded table and failed-solve status](generation-1-expanded-table.png)
- [Optional piano expanded](generation-1-piano.png)

Screenshots contain only the target application and were saved directly from returned Computer Use screenshot data for documentation.
