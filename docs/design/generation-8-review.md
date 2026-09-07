# Generation 8 native design and usability review

Reviewed 7 September 2026, native Windows app process 30060 at 1274 × 800, using Computer Use (`@oai/sky`). Compared against `workspace-system-concept.png`. No implementation edits. This evidence predates the queued persistent ToolPage footer change.

## Grades

- Appearance: **7.5/10**
- Adherence to generated reference: **7/10**
- Usability in the observed workflows: **8/10**
- Hands-on tutorial: **8.5/10**

The Studio score now occupies the primary canvas and the common module navigation, editorial header and right guidance panel form a coherent system. This is substantially closer to the reference than the previous form-first Studio. The application remains less carefully composed than the concept: large generic forms, verbose helper text, flat rectangular selector cards and small scrollable text reports still dominate several workspaces.

## Native interactions verified

1. Opened Studio and loaded Try a sample score. Four parts appeared as simultaneous attacks on a grand staff. Deselecting Soprano, Alto and Tenor updated the overview automatically to the Bass pitches C3–F3–G2–C3, on correct bass-staff positions with clef dots surrounding F3. The Parts control is a toggle-based multiselection; its roughly two-row viewport makes isolating Bass cumbersome.
2. Expanded and collapsed Passage setup. Measure, part, voice, tempo and leap-threshold controls remained accessible. Review voice leading produced the bounded no-findings report for the selected Bass passage. Clicked Play passage and Stop without an error; the UI supplied no playback-progress evidence, so audible output is not claimed.
3. Visited Singing, Jazz and Assignments. Shared headings, module navigation and guidance appeared consistently. Singing and Assignments controls fit. Jazz notation began below the form and report, so the music required scrolling.
4. In Part Writing, Solve harmony returned solution 1/5 with score 6.00. Changing Chorale to Open score preserved the solution and its notation. Play all followed by Stop produced the explicit status “Playback stopped.” The notes remained visible.
5. Home shows useful Piano, Reference, Studio and Tools launch cards above statistics. Its hierarchy is clearer, though it still has two successive welcome/intent headings and no distinctive musical illustration.
6. Resumed a saved tutorial at step 2 with its C3 intact. Continued to step 3: Continue was disabled until clicking the F3 target in chord 2; the exact action produced specific success feedback and enabled Continue. Step 4 required removal: right-clicking chord 2 removed only its Bass note, then enabled Continue with an explanation. The contextual explanation correctly locates C3 and the bass-clef F3 line.

## Remaining improvements

- **High:** Studio sample grand staff grows enough to push Play/Stop and all other actions below the viewport. A persistent footer is essential. Parent has queued this fix for the next process; it is not included in these screenshots or grades.
- **Medium:** Open-score SATB has nested scrolling, and only Soprano/Alto/Tenor are visible at the default position at 1274 × 800. Give the score a more direct full-canvas mode or collapse setup when four-staff viewing is chosen.
- **Medium:** Jazz should prioritize its score over the tall text report, as Score study now does. Singing and Assignments are usable but still resemble generic forms more than the generated workspace composition.
- **Medium:** The Parts selection should show all four standard voices, identify selected parts clearly and explain that clicking toggles selection. Isolating one voice currently requires several clicks and scrolling.
- **Low:** The tutorial sidebar kicker still wraps “FIRST HARMONY” at this width; shorten to a single-line “STEP 3 OF 7.” Tutorial is materially better because it verifies real actions, yet the module-guide landing page remains text-heavy.
- **Low:** Playback in Studio should display a playing/stopped state. A pressed button alone does not tell a learner that anything happened.

## Evidence

- `generation-8-studio.png`: Bass-only passage, visible review report and actions after scrolling.
- `generation-8-solver.png`: solved open-score view after Stop; illustrates the partial score viewport.
- `generation-8-home.png`: task launch cards and current dashboard hierarchy.
- `generation-8-tutorial.png`: F3 placement, exact success feedback and enabled Continue.

No microphone, MIDI hardware or acoustic playback quality claim. No external file publication, import/export round trip or complete curriculum audit in this review.
