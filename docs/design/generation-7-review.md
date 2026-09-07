# Generation 7 native review

Reviewed the running native Windows application (task profile qa-profile-v2, 1274 x 800) using Computer Use, against `workspace-system-concept.png`. This review describes the observed build before the subsequent Studio score-first implementation was restarted.

## Scores

- Appearance: **7/10**
- Reference adherence: **6/10**
- Usability of the sampled workflows: **8/10**
- Tutorial replay and first-note interaction: **8/10**

The shared workspace now has a recognizable structure: compact sidebar, editorial heading, module cards and a consistent guidance rail. Practice no longer overlaps its heading and controls. It is substantially more usable than the prior generation. The reference still puts the music itself earlier and uses much more deliberate compact controls; Studio is the biggest remaining mismatch in this observed build.

## Native actions and observed outcomes

1. Practice: opened an applied-dominant question asking where F# in V7/V leads in C major. Clicked G. Correct feedback explained the semitone resolution and Next remained fully visible. No overlap or clipped answers at the reviewed size.
2. Studio: loaded Try a sample score. The result named First harmony, four parts and 16 pitched events. Clicked Play passage; no error appeared, but audio output was not audibly assessed. Clicked Review voice leading; received a scoped explanation of the checks and no findings. Scrolled down to the notation preview.
3. Piano: clicked the leftmost C2 key. The readout displayed C2 (MIDI 36), and the notation switched to bass clef with C2 on the second ledger line below the staff. The bass dots bracket the F3 line. Keyboard and preview fit together.
4. Reference: clicked D on the circle of fifths. D major / B minor and two sharps F#, C# appeared, with the matching signature. The module guidance was specific to this task.
5. Tools: switched to Metronome. Start produced Playing 4 bars at 90 BPM, with the accented-group explanation. Stop returned the Stopped instruction.
6. Tutorial: replayed the completed first-harmony tour. Continue was disabled until Bass was selected, then enabled with positive feedback. Continued to the C3 target; clicked the ring and received Added C3 - Bass - chord 1 plus validated success. Opened Assignment and verified C3 in the Bass row. Pause & leave returned to Home. This was a replay/first-note regression check, not a repetition of all seven gates tested by Generation 6.

## Remaining design work

- **Studio still puts the music below the fold.** Six large setup fields and seven buttons precede the report and score. The sample is useful, but the screen still initially looks like a form. Put import/sample controls and a meaningful score preview first; move detailed passage settings into a compact disclosure. This was reported to the implementation agent before review completion.
- **Studio notation preview in the observed build flattens all selected parts into a treble-note sequence.** The visual differs sharply from the reference score study. A grouped-attack grand-staff preview would better communicate the sample's four-part harmony. Do not describe a reduced preview as a faithful engraving of arbitrary imported MusicXML.
- Tutorial progress kicker wraps `7` onto its own line at the reviewed width. Use a short separate `Step 2 of 7` label. The header kicker remains PART WRITING STUDIO inside the tutorial; TUTORIAL would clarify location.
- Module cards are clear but visually plain compared with the concept's icons and short descriptive captions. They are an improvement; this is still not a pixel-level match.
- The right rail is often mostly empty below its three instructions. Result-specific guidance/status would use this space better than repeating generic offline text.

## Evidence

- `generation-7-practice.png`: correct answer, explanation and visible Next.
- `generation-7-studio.png`: scrolled report and current notation preview; demonstrates the score hierarchy issue.
- `generation-7-piano.png`: C2 readout and bass staff.
- `generation-7-reference.png`: D major / B minor selection.
- `generation-7-tools.png`: metronome playing status.
- `generation-7-tutorial.png`: replay step 2, direct C3 target and disabled Continue before action.

No implementation files were changed by this reviewer. No microphone, MIDI hardware, export file dialog, arbitrary imported score or audible playback verification was performed in this review. Native UI control has been released.
