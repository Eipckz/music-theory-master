# Score and musicianship studio: v1.4

This release extends the gaps identified after v1.3. See README for all controls, supported formats and limits.

## Implemented additions

1. **Singing practice:** local microphone input and WAV import, monophonic pitch/intonation feedback, target-note exercises and comparison against a selected score line. Explain unvoiced/ambiguous audio; recording is explicit and stops on leaving the screen. No microphone data is uploaded.
2. **MusicXML practice:** safely import local MusicXML/MXL, select parts and passages, control tempo, audition selected lines, and turn a monophonic passage into pitch-entry practice. Retain durations/rests in playback; explain unsupported notation rather than silently claiming full score fidelity.
3. **Jazz study:** graded lessons and listening/keyboard practice covering ii–V–I, guide tones and tritone substitution, plus an interactive progression/voicing workspace. Connect prerequisites to the existing tonal curriculum.
4. **Score-wide voice-leading review:** inspect independent voices beyond a four-slot SATB assignment, identify concrete parallel perfect intervals and melodic issues with locations, and expose the selected checks/limits. This is not a universal counterpoint proof or a full notation editor.
5. **Teacher assignments:** offline JSON exchange, 23 supported topics, deterministic creation, local completion and response-file export/regrading. Offline was retained as the default when no preference for a cloud service was supplied. Answer keys are included and identity/testing conditions are unverified; course progress is unaffected.

## Validation and release gates

- Meaningful engine tests, actual UI interactions, import/export round trips, real/constructed audio fixtures, existing regression suite and packaged-executable self-test.
- Update README's entire feature inventory, developer docs, audit/status notes, skill guidance and synchronized version metadata. Capture fresh real-app photos for current workflows and replace stale primary screenshots.
- Publish source and a new Windows installer/portable release; verify CI, uploaded assets/checksums and the downloaded executable.

Local evidence: the integrated suite passed 526 tests; after adding the truncated-recording regression and final input/display corrections, 47 focused tests passed, plus four repeated Studio interaction checks after the grand-staff adjustment. Lint passed. The release CI runs the complete final suite on Windows/Linux and Python 3.12/3.13.

The v1.4 portable build passed its isolated executable self-test through Qt startup, all Studio tabs, MusicXML import/practice/review, jazz, JSON assignment round trips, WAV pitch tracking, SATB and synthesis. The tagged release repeats this gate for the final artifact. Real-app screenshots were inspected and all four Studio pages checked at 1140×740 and 940×620 with scrolling and no horizontal overflow. README inventory matches 56 skills/59 exercise types; GitHub rendered all 15 tables and 10 expandable sections; local links resolve. The updated expansion skill passed its metadata validator.

Audio verification uses synthesized/harmonic/noisy/silent fixtures, an actual WAV file round trip and a simulated microphone stream to test capture bounds and cleanup. It does not claim calibration against human singing or a live hardware microphone test. The user must explicitly initiate recording, and OS/device availability can affect capture; WAV import remains available.

## Sources

- [music21 MusicXML readers](https://music21.org/music21docs/usersGuide/usersGuide_08_installingMusicXML.html): local score parsing and use of hardened XML handling for untrusted files.
- [sounddevice documentation](https://python-sounddevice.readthedocs.io/en/latest/): explicit local input streams and callback-based recording.
- [Open Music Theory jazz unit](https://viva.pressbooks.pub/openmusictheory/part/jazz/) and [Puget Sound jazz voicings](https://musictheory.pugetsound.edu/mt21c/JazzChordVoicings.html): ii–V–I, guide tones and substitution context.
