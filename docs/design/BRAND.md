# The modern conservatory

Music Theory Master keeps its name and offline desktop identity. The design makes written music the center of the workspace: warm manuscript paper, quiet ink-green surfaces, mint actions, and editorial headings.

## Design source

[Generated brand and solver concept](modern-conservatory-concept.png)

The reference was created with the built-in image generation tool on September 7, 2026. It is a design concept, not a screenshot or proof of functioning software. Application screenshots and independent reviews live alongside this document. The application uses native Qt widgets and vector notation; no controls are baked into a bitmap.

## Tokens and implementation

| Role | Default |
|---|---|
| Canvas | `#101F22` |
| Sidebar | `#0B181B` |
| Panel | `#182D30` |
| Input | `#20363A` |
| Border | `#365156` |
| Primary action | `#A6E3C5` |
| Manuscript | `#F6F1E5` |
| Monogram detail | `#C9A66B` |
| Headings | Georgia, native platform fallback |
| Controls | Segoe UI, Inter, sans-serif fallback |

The compact staff-line M monogram is a native SVG asset. Serif headings and a restrained hierarchy distinguish the app from a generic control panel. Existing light, sepia, high-contrast, accent, and scaling preferences remain available. On ivory score paper, generated/locked notes use a darker green for legibility instead of the light mint button color.

The solver prioritizes key/rules, voice selection, manuscript entry, and solving. The optional piano, assignment table, practice/search settings, file/playback commands, and detailed explanations use named disclosure panels. All previous command handlers remain available. The Home screen now has a learning/solver entry point followed by progress cards in a scrollable layout.

## Final generation prompt

Create a polished high fidelity brand design board and native desktop app UI concept for 'Music Theory Master', a serious but inviting music study and four-part harmony solver application. Wide landscape 1536x1024. Art direction: 'The modern conservatory' — deep ink-green #101F22 background, slightly lighter green panels #182D30, mint #A6E3C5 accent, warm ivory #F6F1E5 manuscript paper, subtle brass secondary accents. Elegant editorial serif headings contrasted with clear sans serif controls. Left 210px navigation sidebar with compact monogram of intersecting staff lines and M, brand Music Theory Master, grouped navigation Learn / Practice / Part Writing / Piano / Reference / Studio / Progress / Settings. Main screen titled 'Make room for harmony.' smaller kicker PART WRITING STUDIO. Clear uncluttered large ivory grand staff showing treble and bass clefs and 4 chords, Roman I IV V I labels. Top compact Key C major, Meter 4/4, Rules Classical, Layout Chorale controls. Above score a segmented Soprano Alto Tenor Bass selector with Bass selected; friendly hint 'Choose a voice. Click the staff to place a note.' Below score small elegant optional piano keyboard, and a prominent mint 'Solve harmony' button and secondary Check and Play. A compact right inspector titled 'Your next step' with notes and solution result. Bottom brand swatches and typography samples in a narrow strip. No busy gradients, no fake windows or photographic hardware, no excessive decoration. This is an implementable Qt desktop visual reference with readable generous spacing, purposeful hierarchy, fine borders, rounded panels, correct-looking musical notation. Make it beautiful, cohesive and professional.

## Intentional adaptations

The native interface uses expandable tools rather than a permanently narrow inspector so the score remains usable on smaller desktop windows. It preserves all 14 navigation destinations rather than dropping screens to copy the concept literally. The generated font suggestion is adapted to installed Windows fonts to keep startup offline. Notation is rendered from actual musical data; the concept's decorative note placement is not treated as musical authority.
