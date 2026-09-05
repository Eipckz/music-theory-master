"""Conflict isolation and learner-facing explanations for SATB work."""

from __future__ import annotations

from collections import Counter

from ..chords import identify_chord, seventh, triad
from .harmony import (
    NormalizedHarmony, harmonies_for_slot, normalize_constraint, tonic_pc,
)
from .models import (
    CadenceType, ChordFactor, PartWritingProblem, RuleCode, RuleEvaluation, RuleSeverity,
    RuleViolation, Voice, VOICE_ORDER, Voicing,
)
from .profiles import RuleProfile, profile_for
from .rules import evaluate_solution


_CLEF_MIDI = {
    "treble": (55, 88),
    "bass": (28, 67),
    "alto": (48, 81),
    "tenor": (40, 74),
}


def _input_error(code: RuleCode, title: str, explanation: str, *, slots=(),
                 voices=(), notes=(), correction="", field="") -> RuleViolation:
    return RuleViolation(code, RuleSeverity.HARD_ERROR, title, explanation,
                         tuple(slots), tuple(voices), tuple(notes), correction, field)


def preflight_diagnostics(problem: PartWritingProblem,
                          profile: RuleProfile) -> list[RuleViolation]:
    issues: list[RuleViolation] = []
    if not problem.slots:
        issues.append(_input_error(
            RuleCode.REQUIRED_CONSTRAINT, "No harmony slots",
            "Add at least one harmonic event before solving.",
            correction="Use Add slot to create a harmonic event.", field="slots"))
        return issues
    if problem.mode not in {"major", "minor"}:
        issues.append(_input_error(
            RuleCode.REQUIRED_CONSTRAINT, "Unsupported mode",
            f"Part writing currently accepts major or minor, not {problem.mode!r}.",
            correction="Choose major or minor.", field="mode"))
    if problem.cadence is not None and len(problem.slots) < 2:
        issues.append(_input_error(
            RuleCode.CADENCE, "Cadence needs two harmonies",
            "A requested cadence requires at least a penultimate and final slot.",
            correction="Add another slot or clear the cadence requirement.", field="cadence"))

    for index, slot in enumerate(problem.slots):
        if slot.duration <= 0:
            issues.append(_input_error(
                RuleCode.REQUIRED_CONSTRAINT, "Invalid duration",
                f"Slot {index + 1} has duration {slot.duration}; duration must be positive.",
                slots=(index,), correction="Enter a positive beat duration.",
                field=f"slot.{index}.duration"))
        try:
            harmonies = harmonies_for_slot(problem, index)
        except ValueError as exc:
            issues.append(_input_error(
                RuleCode.HARMONY_LABEL_CONFLICT, "Conflicting harmony labels", str(exc),
                slots=(index,), correction="Make the Roman numeral, chord symbol, figure, and inversion agree.",
                field=f"slot.{index}.harmony"))
            harmonies = []
        explicit_label = slot.harmony.roman_numeral or slot.harmony.chord_symbol
        if explicit_label and explicit_label.strip().lower() in {
                label.strip().lower() for label in slot.harmony.forbidden_harmonies}:
            issues.append(_input_error(
                RuleCode.REQUIRED_CONSTRAINT, "Required harmony is forbidden",
                f"Slot {index + 1} requires {explicit_label}, but the same harmony is forbidden.",
                slots=(index,), correction="Remove either the required or forbidden chord label.",
                field=f"slot.{index}.harmony"))
        if not harmonies:
            issues.append(_input_error(
                RuleCode.UNSUPPORTED_HARMONY, "No supported harmony candidate",
                f"Slot {index + 1} has no harmony that the current grammar can realize.",
                slots=(index,), correction="Enter a supported Roman numeral or chord symbol.",
                field=f"slot.{index}.harmony"))

        locked_notes = []
        for voice in VOICE_ORDER:
            constraint = slot.voice(voice)
            exact = constraint.pitch.exact
            if exact is None:
                continue
            locked_notes.append((voice, exact))
            allowed = profile.voice_ranges[voice]
            if not allowed.contains(exact):
                issues.append(_input_error(
                    RuleCode.RANGE, "Locked pitch is outside its voice range",
                    f"Slot {index + 1} {voice.value} is locked to {exact.name}, outside "
                    f"{allowed.minimum.name}-{allowed.maximum.name}.",
                    slots=(index,), voices=(voice,), notes=(exact.name,),
                    correction=f"Unlock {voice.value} or move it into range.",
                    field=f"slot.{index}.{voice.value}"))
            if constraint.clef is not None:
                low, high = _CLEF_MIDI[constraint.clef.value]
                if not low <= exact.midi <= high:
                    issues.append(_input_error(
                        RuleCode.REQUIRED_CONSTRAINT, "Clef is unsuitable for the locked pitch",
                        f"{exact.name} is outside the practical display range of {constraint.clef.value} clef.",
                        slots=(index,), voices=(voice,), notes=(exact.name,),
                        correction="Choose a suitable clef or a nearer pitch.",
                        field=f"slot.{index}.{voice.value}.clef"))
            if harmonies and all(
                    exact.name_no_octave
                    not in {member.name_no_octave for member in harmony.members}
                    for harmony in harmonies):
                issues.append(_input_error(
                    RuleCode.CHORD_MEMBERSHIP, "Locked pitch is not in the required harmony",
                    f"Slot {index + 1} {voice.value} is locked to {exact.name}, which is not "
                    "a correctly spelled member of any allowed harmony.",
                    slots=(index,), voices=(voice,), notes=(exact.name,),
                    correction=f"Change or unlock the {voice.value} pitch, or change the harmony.",
                    field=f"slot.{index}.{voice.value}"))
            if voice == Voice.BASS and harmonies and all(
                    exact.name_no_octave
                    != harmony.members[harmony.inversion].name_no_octave
                    for harmony in harmonies):
                issues.append(_input_error(
                    RuleCode.INVERSION, "Locked bass contradicts the inversion",
                    f"Slot {index + 1} locks bass {exact.name}, but the selected inversion "
                    "requires a different bass chord member.",
                    slots=(index,), voices=(Voice.BASS,), notes=(exact.name,),
                    correction="Unlock the bass or change the inversion/figure.",
                    field=f"slot.{index}.bass"))
        locked = dict(locked_notes)
        for upper, lower in ((Voice.SOPRANO, Voice.ALTO), (Voice.ALTO, Voice.TENOR),
                             (Voice.TENOR, Voice.BASS)):
            if upper in locked and lower in locked and locked[lower].midi > locked[upper].midi:
                issues.append(_input_error(
                    RuleCode.VOICE_CROSSING, "Locked voices cross",
                    f"Slot {index + 1} locks {lower.value} {locked[lower].name} above "
                    f"{upper.value} {locked[upper].name}.",
                    slots=(index,), voices=(upper, lower),
                    notes=(locked[upper].name, locked[lower].name),
                    correction=f"Unlock or move the {upper.value} or {lower.value} note.",
                    field=f"slot.{index}.{lower.value}"))
        if len(locked_notes) == 4 and slot.harmony.required_doubling is not None and len(harmonies) == 1:
            harmony = harmonies[0]
            count = sum(harmony.factor_for(note) == slot.harmony.required_doubling
                        for _, note in locked_notes)
            if count < 2:
                issues.append(_input_error(
                    RuleCode.REQUIRED_DOUBLING, "Locked notes contradict required doubling",
                    f"All four voices are locked, but the chordal "
                    f"{slot.harmony.required_doubling.value} is not doubled.",
                    slots=(index,), correction="Unlock one voice or change the required doubling.",
                    field=f"slot.{index}.required_doubling"))
        if len(locked_notes) == 4 and len(harmonies) == 1 and profile.require_complete_triads:
            harmony = harmonies[0]
            if len(harmony.factors) == 3:
                present = {harmony.factor_for(note) for _, note in locked_notes}
                missing = set(harmony.factors) - present
                if missing:
                    names = ", ".join(sorted(factor.value for factor in missing))
                    issues.append(_input_error(
                        RuleCode.CHORD_COMPLETENESS, "Locked notes omit a required chord member",
                        f"All voices in slot {index + 1} are locked, but the {names} is absent.",
                        slots=(index,), notes=tuple(note.name for _, note in locked_notes),
                        correction="Unlock a duplicated chord tone or change the harmony.",
                        field=f"slot.{index}"))

    if problem.cadence is not None and len(problem.slots) >= 2:
        penultimate = problem.slots[-2]
        final = problem.slots[-1]
        explicit = all(slot.harmony.roman_numeral or slot.harmony.chord_symbol
                       for slot in (penultimate, final))
        if explicit:
            try:
                before = harmonies_for_slot(problem, len(problem.slots) - 2)
                after = harmonies_for_slot(problem, len(problem.slots) - 1)
                tonic = tonic_pc(problem.key_tonic)
                dominant = (tonic + 7) % 12
                subdominant = (tonic + 5) % 12
                deceptive = (tonic + (9 if problem.mode == "major" else 8)) % 12
                expected = {
                    CadenceType.PERFECT_AUTHENTIC: (dominant, tonic),
                    CadenceType.IMPERFECT_AUTHENTIC: (dominant, tonic),
                    CadenceType.HALF: (None, dominant),
                    CadenceType.DECEPTIVE: (dominant, deceptive),
                    CadenceType.PLAGAL: (subdominant, tonic),
                }[problem.cadence]
                matches = bool(before and after) and (
                    expected[0] is None or before[0].chord.root.pc == expected[0]) \
                    and after[0].chord.root.pc == expected[1]
                if not matches:
                    issues.append(_input_error(
                        RuleCode.CADENCE, "Final harmonies contradict the cadence",
                        f"The explicit final progression cannot form the requested "
                        f"{problem.cadence.value} cadence.",
                        slots=(len(problem.slots) - 2, len(problem.slots) - 1),
                        correction="Change the final harmonies or clear the cadence requirement.",
                        field="cadence"))
            except ValueError:
                pass
    return issues


def inferred_harmonies(problem: PartWritingProblem,
                       voicings: list[Voicing]) -> tuple[list[NormalizedHarmony], list[RuleViolation]]:
    harmonies: list[NormalizedHarmony] = []
    issues: list[RuleViolation] = []
    for index, (slot, voicing) in enumerate(zip(problem.slots, voicings)):
        if slot.harmony.roman_numeral or slot.harmony.chord_symbol:
            try:
                harmonies.append(normalize_constraint(
                    slot.harmony, problem.key_tonic, problem.mode))
                continue
            except ValueError as exc:
                issues.append(_input_error(
                    RuleCode.HARMONY_LABEL_CONFLICT, "Harmony label conflict", str(exc),
                    slots=(index,), field=f"slot.{index}.harmony"))
                continue
        info = identify_chord(list(voicing.notes))
        if info is None:
            issues.append(_input_error(
                RuleCode.CHORD_MEMBERSHIP, "Chord cannot be inferred",
                f"The four notes in slot {index + 1} do not form a supported tertian chord.",
                slots=(index,), notes=voicing.spelled_tuple,
                correction="Correct the vertical sonority or provide its intended harmony."))
            continue
        root = info["root"]
        quality = info["quality"]
        unique_count = len({note.pc for note in voicing.notes})
        chord = (seventh(root, quality) if unique_count == 4
                 else triad(root, quality))
        chord.inversion = info["inversion"]
        factors = (ChordFactor.ROOT, ChordFactor.THIRD, ChordFactor.FIFTH,
                   ChordFactor.SEVENTH)[:len(chord.members)]
        harmonies.append(NormalizedHarmony(
            f"{root.name_no_octave} {quality}", chord, factors, info["inversion"]))
    return harmonies, issues


def check_solution(problem: PartWritingProblem, voicings: list[Voicing],
                   profile: RuleProfile | None = None) -> RuleEvaluation:
    profile = profile or profile_for(problem.profile_id)
    if len(voicings) != len(problem.slots):
        return RuleEvaluation([_input_error(
            RuleCode.REQUIRED_CONSTRAINT, "Incomplete progression",
            f"The problem has {len(problem.slots)} slots but {len(voicings)} voicings were supplied.",
            correction="Complete every slot before checking.")])
    harmonies, issues = inferred_harmonies(problem, voicings)
    if issues or len(harmonies) != len(voicings):
        return RuleEvaluation(issues)
    return evaluate_solution(problem, harmonies, voicings, profile)


def no_solution_diagnostics(problem: PartWritingProblem, profile: RuleProfile,
                            empty_slots: list[int], rejection_counts: Counter,
                            samples: dict[RuleCode, RuleViolation]) -> list[RuleViolation]:
    issues = preflight_diagnostics(problem, profile)
    if issues:
        return issues
    for index in empty_slots:
        issues.append(_input_error(
            RuleCode.REQUIRED_CONSTRAINT, "Slot has no legal voicing",
            f"Slot {index + 1} has no voicing that satisfies its harmony, locks, ranges, spacing, and doubling.",
            slots=(index,), correction=f"Review or unlock constraints in slot {index + 1}.",
            field=f"slot.{index}"))
    if issues:
        return issues
    for code, _count in rejection_counts.most_common(6):
        sample = samples.get(code)
        if sample is not None:
            issues.append(sample)
    if not issues:
        issues.append(_input_error(
            RuleCode.REQUIRED_CONSTRAINT, "No legal path through the progression",
            "Every local chord can be voiced, but the transitions cannot all satisfy the selected profile.",
            correction="Unlock a note, change an inversion, or compare the Common Practice profile."))
    return issues


def summarize(violations: list[RuleViolation]) -> str:
    if not violations:
        return "No hard-rule violations were found."
    ordered = sorted(violations, key=lambda item: (
        item.slots[0] if item.slots else 10**9,
        0 if item.severity == RuleSeverity.HARD_ERROR else 1,
        item.code.value,
    ))
    return "\n".join(
        f"{index + 1}. {item.title}: {item.explanation}"
        + (f" Suggested correction: {item.correction}" if item.correction else "")
        for index, item in enumerate(ordered)
    )


RULE_EXPLANATIONS = {
    RuleCode.PARALLEL_FIFTH: (
        "Parallel perfect fifths weaken the independence of the same two voices. "
        "The check uses voice identity and interval class, so fifth-to-twelfth counts too."
    ),
    RuleCode.PARALLEL_OCTAVE: (
        "Parallel octaves and unison-octave exchanges make two parts sound like one line."
    ),
    RuleCode.PARALLEL_FOURTH: (
        "Parallel fourths between upper voices are accepted in Common Practice; stricter profiles may forbid them."
    ),
    RuleCode.HIDDEN_FIFTH: (
        "A direct fifth matters chiefly in the outer voices when both move similarly and the soprano leaps."
    ),
    RuleCode.LEADING_TONE_RESOLUTION: (
        "A functional leading tone normally rises by a spelled step to the tonic it tonicizes."
    ),
    RuleCode.CHORDAL_SEVENTH_RESOLUTION: (
        "A chordal seventh is a directed dissonance and normally descends by step."
    ),
    RuleCode.VOICE_OVERLAP: (
        "Overlap occurs across two chords when a voice moves beyond the previous position of an adjacent voice."
    ),
}


def explain(code: RuleCode) -> str:
    return RULE_EXPLANATIONS.get(code, "This rule is evaluated under the selected profile.")
