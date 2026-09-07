# The modern conservatory

Music Theory Master keeps its name and offline desktop identity. The design makes written music the center of the workspace: warm manuscript paper, quiet ink-green surfaces, mint actions, and editorial headings.

## Design source

[Original brand concept](modern-conservatory-concept.png) · [Current four-workspace reference](workspace-system-concept.png)

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

The second iteration implements the reference's composition rather than only its palette. `workspace.py` provides an editorial header, module cards and a contextual coach. Every original destination remains, with Tutorial added. Tool and Studio pages share balanced fields, a scrollable canvas and a fixed action footer. The solver uses Write, Assignment, Practice & rules and Listen & files cards, with its action row outside the score scroll area and diagnostics in the coach. Score study puts import/sample controls and an actual pitch overview before collapsible passage settings.

Tutorial uses the real part-writing editor with a separate key-value store. Seven action gates teach voice choice, bass positions, correction, solving, playback and assignment data. It is resumable, skippable and repeatable. The main assignment autosave and coursework database are never substituted with training data.

## Original generation prompt

Create a polished high fidelity brand design board and native desktop app UI concept for 'Music Theory Master', a serious but inviting music study and four-part harmony solver application. Wide landscape 1536x1024. Art direction: 'The modern conservatory' — deep ink-green #101F22 background, slightly lighter green panels #182D30, mint #A6E3C5 accent, warm ivory #F6F1E5 manuscript paper, subtle brass secondary accents. Elegant editorial serif headings contrasted with clear sans serif controls. Left 210px navigation sidebar with compact monogram of intersecting staff lines and M, brand Music Theory Master, grouped navigation Learn / Practice / Part Writing / Piano / Reference / Studio / Progress / Settings. Main screen titled 'Make room for harmony.' smaller kicker PART WRITING STUDIO. Clear uncluttered large ivory grand staff showing treble and bass clefs and 4 chords, Roman I IV V I labels. Top compact Key C major, Meter 4/4, Rules Classical, Layout Chorale controls. Above score a segmented Soprano Alto Tenor Bass selector with Bass selected; friendly hint 'Choose a voice. Click the staff to place a note.' Below score small elegant optional piano keyboard, and a prominent mint 'Solve harmony' button and secondary Check and Play. A compact right inspector titled 'Your next step' with notes and solution result. Bottom brand swatches and typography samples in a narrow strip. No busy gradients, no fake windows or photographic hardware, no excessive decoration. This is an implementable Qt desktop visual reference with readable generous spacing, purposeful hierarchy, fine borders, rounded panels, correct-looking musical notation. Make it beautiful, cohesive and professional.

## Intentional adaptations

Native controls remain interactive and accessible; there are no bitmap controls. The reference's fonts are adapted to installed fonts to keep startup offline. All original navigation destinations and command handlers remain available. Long scores and expanded setup areas scroll while principal task actions stay visible. Notation comes from actual musical data; decorative note placement in the concept is not treated as musical authority. Studio's preview is a pitch overview of the first twelve selected attack times, not a complete MusicXML engraving engine.

## Second-generation image brief

The four-workspace board was generated on September 7, 2026 using the built-in image tool. The brief requested a 1536×1024, 2×2 board showing Part Writing, Studio, Practice and first-run Tutorial, all using the same modern-conservatory system:

- Forest canvas `#101F22`, panels `#182D30`, mint `#A6E3C5`, brass `#C9A66B`, ivory `#F6F1E5`; Georgia and Segoe-style typography.
- Compact icon navigation, editorial headings, module cards and a roughly 72/28 music-canvas/coach split.
- Part Writing with Write / Assignment / Practice / Listen & export, a large score, compact piano, solution status and an anchored action row.
- Studio with Score study / Sing & listen / Jazz / Assignments and a visible score passage.
- Practice with Theory / Ear training / Keyboard and a focused notation question.
- A hands-on tutorial showing a marked C3 bass target, genuine completion feedback, step progress, Previous / Continue and Skip.

The reference is retained for honest side-by-side review. Generation 5 explicitly rejected the first implementation's match; the subsequent reports document both functional progress and remaining visual differences.
