# Part-writing development

Use this guide when changing the Four-Part Writing Lab. Read `CLAUDE.md` first.

## Non-negotiable contracts

- Keep `music_theory/theory/part_writing/` independent of Qt and runtime network access.
- Keep `Note` objects and their spelling through normalization, constraints, rules, ranking, and export. C# and Db are not interchangeable analysis labels.
- A hard user constraint is immutable. The solver must honor every hard constraint or return `INVALID_INPUT`, `NO_SOLUTION`, `TIMEOUT`, or `CANCELLED`; it must never silently relax one.
- Every returned solution must pass `validate_returned_solution()` with zero hard violations.
- Correctness is evaluated under the selected `RuleProfile`. Do not claim that one profile represents every textbook or instructor.
- Keep music21 lazy. It may parse Roman numerals and write MusicXML, but the custom rule engine is the source of truth.

## Architecture

1. `models.py` defines the version-stable problem, constraint, voicing, violation, solution, and solver-option types.
2. `profiles.py` assigns every named rule a severity and carries voice ranges, options, and soft-ranking weights.
3. `harmony.py` normalizes explicit or grammar-supplied labels into correctly spelled root-position chord members plus inversion metadata.
4. `rules.py` contains small named local, transition, three-event, special-resolution, and cadence validators returning structured `RuleViolation` data.
5. `voicings.py` enumerates and caches vertical candidates. Its cache key must include every constraint or profile option that can change candidate legality or score.
6. `solver.py` builds an exact layered candidate graph, rejects illegal edges, retains deterministic top-K paths, and independently validates complete results.
7. `diagnostics.py` catches contradictions before search and turns rejection evidence into field-specific learner guidance.
8. `generator.py` solves a complete template first, removes clues by `PracticeType`, then proves the masked problem remains solvable (and unique when requested).
9. `serialization.py` owns versioned JSON; `export.py` owns lazy MusicXML conversion.
10. `ui/screens/part_writing.py` connects the model-backed editor, worker, diagnostics, local persistence, audio, course guide, and export. `ui/widgets/satb_staff.py` preserves SATB voice identity.

## Supported harmony vocabulary

- Major/minor diatonic triads and seventh chords, Roman case/quality, and root/first/second/third inversions.
- Figured bass `5/3`, `6/3`, `6/4`, `7`, `6/5`, `4/3`, and `4/2` plus compact forms.
- Chord symbols for major, minor, diminished, augmented, dominant seventh, major seventh, minor seventh, half-diminished seventh, and fully diminished seventh, including chord-member slash basses.
- Applied Roman numerals handled by the existing parser, including dominant and leading-tone chords such as `V/V`, `V7/IV`, and `viio7/V`.
- Mixture labels accepted by the Roman parser, including `bVI`, `bVII`, and minor iv in major.
- Dedicated spellings/rules for `N6`, `It+6`, `Fr+6`, `Ger+6`, and cadential `I64`/`i64` to V.
- Authentic (perfect/imperfect), half, deceptive, and plagal cadence requirements.

## Deliberate unsupported cases

- Arbitrary non-tertian sonorities, clusters, polychords, quartal harmony, and arbitrary user-defined chord formulas.
- Mode-wide part-writing beyond major/minor, enharmonic reinterpretation as a modulation mechanism, and an unrestricted functional-harmony grammar.
- Suspensions, passing tones, anticipations, and other non-chord-tone events as independently timed entities. Every sounding note currently belongs to its slot harmony.
- Species-counterpoint rhythm semantics beyond the stricter reusable profile.
- Universal correctness across historical styles, textbooks, or instructor policies.

When input is outside the vocabulary, return a clear unsupported-harmony diagnostic. Do not guess.

## Rule profiles

`COMMON_PRACTICE` allows parallel fourths and applies contextual hidden-perfect and melodic policies. `CLASSROOM_STRICT` makes disputed perfect-interval and melodic rules hard. `SPECIES_COUNTERPOINT` is a conservative reusable variant. `CUSTOM` is a deep copy with locally serialized severities, ranges, weights, and behavioral options.

`HARD_ERROR` invalidates a candidate. `CONDITIONAL_ERROR` is reported without invalidating it. `SOFT_PENALTY` ranks but does not invalidate. `PREFERENCE_BONUS` lowers rank cost. `DISABLED` omits the violation.

## Solver behavior

The solver is deterministic for the same problem, profile, options, and seed. It normalizes each slot, enumerates locally legal SATB voicings, then performs dynamic programming across adjacent transitions while retaining up to top-K paths per state. Ranking cost favors lower total motion, common tones, stepwise upper voices, contrary bass motion, usable ranges, standard doubling, and balanced spacing. Ties use spelled harmony/voicing tuples.

`max_nodes`, `time_limit_seconds`, and a `threading.Event` cancellation token are honest terminal bounds. A bound returns no partial answer as if it were proven. UI work runs in `_SolveWorker` and communicates only through Qt signals.

## JSON schema

`schema_version` is currently `1`. Kinds are `part-writing-problem`, `part-writing-profile`, and `part-writing-solution`. Problems preserve key/mode, meter, cadence, profile, layout, tempo, title, seed, slot durations/labels, every harmony constraint, per-voice pitch constraint, locks, clefs, note/source labels, allowed pitch sets, and pitch bounds. Profiles preserve rule-code severities, soft weights, four ranges, and options. Solutions preserve spelled SATB pitches, score/breakdown, and harmony labels.

Only use JSON through `serialization.py`. Never add pickle, `eval`, or permissive schema fallbacks. Increment the schema version and add explicit migration behavior for a breaking representation change.

## Verification

Run the focused suite:

```powershell
python -m pytest tests/test_part_writing_models.py -q
python -m pytest tests/test_part_writing_rules.py -q
python -m pytest tests/test_part_writing_solver.py -q
python -m pytest tests/test_part_writing_generator.py -q
python -m pytest tests/test_part_writing_diagnostics.py -q
python -m pytest tests/test_part_writing_serialization.py -q
python -m pytest tests/test_part_writing_gui.py -q
python -m pytest tests/test_part_writing_export.py -q
```

Then run the full test and lint gates from `CLAUDE.md`, live-launch verification from `.claude/skills/verify-app/SKILL.md`, and `./build.ps1` when packaging-relevant code changed.

## Add a new rule

1. Add a stable `RuleCode` without changing existing values.
2. Assign a default severity in `_common_rules()` and decide stricter/custom presentation.
3. Implement one named validator or extend the narrowest existing validator. Always return title, explanation, slots, voices, notes, correction, and field when applicable.
4. Call it at the correct local/transition/three-event/cadence layer. Do not duplicate the check in the solver.
5. If legality or local score changes, add the relevant profile/constraint value to the voicing cache signature.
6. Add isolated valid and invalid tests, a profile-disagreement test when disputed, and an end-to-end solver revalidation test.
7. Add learner text to `RULE_EXPLANATIONS` and the custom profile dialog when appropriate.

## Add a special chromatic chord handler

1. Add explicit aliases and diatonic spelling in `_special_harmony()`; derive altered degrees by letter and accidental, not MIDI class alone.
2. Return root-position members, inversion, factors, and a stable `special` discriminator.
3. Add required doubling/completeness behavior in `validate_chord()` only when stylistically justified by the profile.
4. Add directed-tone behavior in `validate_special_resolution()` or `validate_tendency_tones()`.
5. Add normalization tests in multiple keys/modes, isolated good/bad resolution fixtures, at least one solvable progression, serialization/export checks, and a generator template only after those pass.

## Add a practice type

1. Add a stable `PracticeType` value.
2. Extend `_apply_mask()` to remove only the intended clues and leave locks explicit.
3. Add instructions that ask the learner to make decisions before revealing the answer.
4. Use only the passed `random.Random`; never module-global randomness.
5. Prove the canonical answer self-grades, the masked problem has a solution, requested uniqueness is real, and a fixed seed reproduces the same problem and answer.
6. Add the type to UI selection; registered curriculum drills may choose it by difficulty if pedagogically appropriate.
