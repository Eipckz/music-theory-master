# Generation 5 — strict visual reference review

2026-09-07. Independent critique of `modern-conservatory-concept.png` against the saved Generation 2–4 Home, Learn, Reference, Studio and solver screenshots. **Appearance: 5/10. Reference adherence: 3/10. Functionality: not regraded**; this review did not interact with the running app. Prior successful interactions establish individual behaviors, not an excellent end-to-end experience. No code changes or native interactions were made; UI control is released.

The user's objection is supported by the screenshots. The app reproduces the concept's colors and some typography, but not its composition, hierarchy or contextual guidance. A coherent palette alone does not earn an 8.5. The concept gives music a generous central canvas, surrounds it with compact controls, and explains the next action in an adjacent panel. The implementation is mostly stacked legacy forms with themed widgets.

## Required shared workspace contract

- **Shell:** compact branded sidebar with consistent line icons, readable grouped navigation, a clear current-page indicator, and Help/Settings reachable at 1280×800. Avoid large branding pushing navigation below the fold. Keep the mark and title aligned; use one spacing scale throughout (8/16/24 px).
- **Header:** small gold category, one editorial serif title, one short task-oriented sentence; a consistent “Take a tour” control. Body text and control labels use a highly legible sans serif, never the decorative title font.
- **Work area:** compact contextual setup row, approximately 72% task canvas / 28% guidance rail. The rail states the next step, relevant explanation and actual current result. Reflow it below the canvas at narrow sizes; do not compress controls or text until they clip.
- **Actions:** one mint primary action, secondary outlined actions, tertiary quiet actions. Keep the primary action visible while a large score scrolls. Advanced settings belong in labeled disclosure sections and retain every existing capability.
- **States:** meaningful empty-state illustration or sample with one starting action; clear loading/disabled/result/error states. No large unexplained empty boxes or zero-filled dashboards. Align card edges, baseline labels and control heights; avoid borders around every nested container.

## Priority redesign work

1. **Solver:** restore the concept's score-plus-guidance composition; keep voice tabs adjacent to the staff, explain which staff accepts input, show the selected note/slot, provide undo/delete guidance, and expose the optional piano without displacing the score. Pin Solve / Check / Play. Layout changes should preserve solutions. Separate open-score staves enough that opposite stems cannot appear joined; verify bass placement through actual clicks and displayed pitch feedback.
2. **Studio:** replace the wall of six equally prominent buttons with “Open a score” → score preview → passage selection → one next action. Put tempo/measure controls together and review/practice/singing in clear task destinations. Explain disabled actions before importing a score.
3. **Learn/Practice:** turn the near-empty lecture canvas into a focused lesson card with an actual staff/example, then an interactive task. Show what is being practiced, progress and feedback together. Offer guided practice presets before advanced configuration.
4. **Reference/Piano/Tools:** give every submodule a visible purpose and the same setup/canvas/guidance/action anatomy. Reference already has a useful two-column start, but needs a framed explanation/action panel and less unstructured blank space. Piano should foreground the musical example and place root/quality/scale controls in named groups.
5. **Home:** prioritize “Start your first lesson,” “Try harmony” and resume work. Empty XP/streak/accuracy cards are secondary information, not the first-time experience.

## Tutorial acceptance criteria

First launch offers a skippable, restartable hands-on path; the Help entry always reopens it. Let users choose a goal, demonstrate the app's major destinations, then complete a real small task: choose Bass, click a specified staff location, confirm the displayed pitch, correct/remove it, solve a safe example, inspect feedback and play it. Each step explains **why**, anchors to the actual control, and advances on the expected action rather than merely a Next button. Include Back, progress, exit/resume, keyboard guidance and explicit completion. Never overwrite existing work: use a labeled tutorial exercise or restore a snapshot. Supply shorter contextual tours for the other modules. Verify first launch, skipped/restarted tours, interruption and completion with native Computer Use, including smaller-window clipping and preservation of user work.

Release gate: compare new screenshots directly against the new generated multi-workspace concept, not against the previous implementation. Independently grade visual match and usability; report untested functionality rather than inflating a composite score.
