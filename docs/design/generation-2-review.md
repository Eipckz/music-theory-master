# Generation 2 design and usability review

Reviewed the live Music Theory Master native window through Windows Computer Use (`@oai/sky`), with fresh screenshots and real clicks. No application code was edited by this reviewer.

**Appearance: 8/10. Observed usability: 8/10.** The visual grade covers Home, Part Writing, Learn, Reference and Studio. The functional grade concerns the solver interactions actually performed. The build reviewed precedes the parent's subsequent bass-glyph and card-button fixes.

## Verified human paths

- Navigated from Placement to Home and Part Writing using the persistent sidebar. The new monogram, forest background, cream score, mint accents, serif headings and Home cards feel coherent. Home offers a direct harmony-studio entry point.
- Expanded More actions, scrolled to Reset and reset to the four-chord exercise. Solve harmony progressed from Solving to **Solution 1/5, score 6.00**, displaying all four voices across the I-IV-V-I progression.
- Selected Bass. Entered **C3 in chord 1** and **F3 in chord 2** by clicking the score. Editing switched the solved display to the true partial input: exactly two bass notes, with unknown voices blank.
- Right-clicked the second chord to remove its bass note; the note disappeared and the status confirmed removal.
- Expanded the optional piano, scrolled to its labeled keyboard and clicked the F3 key. F3 returned to the selected second bass cell, with the status **Added F3 to 1 selected voice cell(s).**
- Visited Learn, Reference and Studio. Their content and retained sub-tabs rendered, and the shared shell/navigation remained consistent and readable.

## Coordinate calibration finding

The screenshot was 1274 x 800, originX 9, originY 0. With Computer Use's observed native-frame offset compensated by clicking 8 pixels above the screenshot target, pitch placement was correct: visual C3 y501 / click y493 produced C3; visual F3 y478 / click y470 produced F3. This is evidence against changing the app's staff pitch mathematics to compensate for the automation runtime. The resulting rendered notes sit in the correct C3 space and on the F3 line.

## Findings sent to the implementer

1. The bass-clef glyph's dots still appeared about half a staff space too low: the upper dot roughly on the F3 line instead of above it. Unlike the click offset, this is visible in the rendered screenshot. The implementer reports finding and fixing the glyph offset after this review; that fix is not included in this generation's inspected build.
2. Home's Continue learning button used almost-black text on the dark card, making it difficult to read. Placement showed a similar issue. The implementer reports removing the overly broad card-child transparency selector after this review. Final screenshots should verify the repaired contrast.
3. Studio is coherent but retains a dense form and six equally emphasized mint buttons. A future hierarchy refinement could emphasize Open MusicXML until a score is loaded. This is optional polish, not a demonstrated functional failure.
4. Learn's opening staff lesson is readable but mostly empty text space; an actual staff illustration would strengthen instruction. No lesson content was changed in this review.

## Coverage boundaries

This bounded native review demonstrated successful harmony solving, direct bass entry, partial-score preservation, note removal, optional piano input and navigation to five feature areas. It did not verify audio audibility, MIDI hardware, microphone/singing, import/export round trips, all key signatures/meters/layouts, every course question or all historical feature parity. Automated test results are not used as substitutes for these native observations.

## Screenshot evidence

- [Home](generation-2-home.png)
- [Successful solve](generation-2-solved.png)
- [Two directly entered bass notes](generation-2-partial-bass.png)
- [Piano entry into the selected bass cell](generation-2-piano-entry.png)
- [Learn](generation-2-learn.png)
- [Reference](generation-2-reference.png)
- [Studio](generation-2-studio.png)

These screenshots contain only the application and were saved directly from returned Computer Use screenshot data for documentation. The UI is released to the main agent after this review.
