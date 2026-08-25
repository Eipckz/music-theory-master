"""Named, testable SATB rules with structured diagnostics."""

from __future__ import annotations

from collections import Counter
import re

from ..chords import identify_chord
from ..pitch import Note, interval_between
from .harmony import (
    NormalizedHarmony, scale_degree, temporary_leading_tone_pc, tonic_pc,
)
from .models import (
    CadenceType, ChordFactor, PartWritingProblem, RuleCode, RuleEvaluation,
    RuleSeverity, RuleViolation, Voice, VOICE_ORDER, Voicing,
)
from .profiles import RuleProfile


_PAIRS = tuple(
    (VOICE_ORDER[i], VOICE_ORDER[j])
    for i in range(len(VOICE_ORDER)) for j in range(i + 1, len(VOICE_ORDER))
)
_ADJACENT = ((Voice.SOPRANO, Voice.ALTO), (Voice.ALTO, Voice.TENOR),
             (Voice.TENOR, Voice.BASS))


def _severity(profile: RuleProfile, code: RuleCode) -> RuleSeverity:
    return profile.severity(code)


def _violation(profile: RuleProfile, code: RuleCode, title: str, explanation: str,
               *, slots=(), voices=(), notes=(), correction="", field="") -> RuleViolation | None:
    severity = _severity(profile, code)
    if severity == RuleSeverity.DISABLED:
        return None
    return RuleViolation(code, severity, title, explanation, tuple(slots), tuple(voices),
                         tuple(notes), correction, field)


def _add(evaluation: RuleEvaluation, violation: RuleViolation | None) -> None:
    if violation is not None:
        evaluation.violations.append(violation)
        if violation.severity == RuleSeverity.SOFT_PENALTY:
            evaluation.soft_score += 5.0
            name = f"Soft rule: {violation.title}"
            evaluation.score_breakdown[name] = evaluation.score_breakdown.get(name, 0.0) + 5.0
        elif violation.severity == RuleSeverity.PREFERENCE_BONUS:
            evaluation.soft_score -= 2.0
            name = f"Preference: {violation.title}"
            evaluation.score_breakdown[name] = evaluation.score_breakdown.get(name, 0.0) - 2.0


def _spelled_member_index(note: Note, harmony: NormalizedHarmony) -> int | None:
    for index, member in enumerate(harmony.members):
        if note.name_no_octave == member.name_no_octave:
            return index
    return None


def _factor_counts(voicing: Voicing, harmony: NormalizedHarmony) -> Counter:
    counts = Counter()
    for note in voicing.notes:
        factor = harmony.factor_for(note)
        if factor is not None:
            counts[factor] += 1
    return counts


def _constraint_matches(note: Note, constraint, harmony: NormalizedHarmony,
                        key_tonic: str, mode: str) -> tuple[bool, str]:
    pitch = constraint.pitch
    if pitch.exact is not None and note != pitch.exact:
        return False, f"requires exact pitch {pitch.exact.name}"
    if pitch.pitch_class is not None \
            and note.name_no_octave != pitch.pitch_class.name_no_octave:
        return False, f"requires pitch class {pitch.pitch_class.name_no_octave}"
    if pitch.scale_degree is not None \
            and scale_degree(note, key_tonic, mode) != pitch.scale_degree:
        return False, f"requires scale degree {pitch.scale_degree}"
    if pitch.chord_factor is not None and harmony.factor_for(note) != pitch.chord_factor:
        return False, f"requires the chordal {pitch.chord_factor.value}"
    if pitch.allowed_pitches:
        allowed = {candidate.name for candidate in pitch.allowed_pitches}
        allowed_pc = {candidate.name_no_octave for candidate in pitch.allowed_pitches}
        if note.name not in allowed and note.name_no_octave not in allowed_pc:
            return False, "is not one of the allowed pitches"
    if pitch.minimum is not None and note.midi < pitch.minimum.midi:
        return False, f"must be at or above {pitch.minimum.name}"
    if pitch.maximum is not None and note.midi > pitch.maximum.midi:
        return False, f"must be at or below {pitch.maximum.name}"
    return True, ""


def validate_voice_ranges(slot_index: int, voicing: Voicing,
                          profile: RuleProfile) -> RuleEvaluation:
    result = RuleEvaluation()
    for voice in VOICE_ORDER:
        note = voicing[voice]
        allowed = profile.voice_ranges[voice]
        if not allowed.contains(note):
            _add(result, _violation(
                profile, RuleCode.RANGE, "Voice outside its range",
                f"{voice.value.title()} {note.name} is outside the configured "
                f"range {allowed.minimum.name}-{allowed.maximum.name}.",
                slots=(slot_index,), voices=(voice,), notes=(note.name,),
                correction=f"Move {voice.value} into its configured range.",
                field=f"slot.{slot_index}.{voice.value}",
            ))
    return result


def validate_voice_order_and_spacing(slot_index: int, voicing: Voicing,
                                     profile: RuleProfile) -> RuleEvaluation:
    result = RuleEvaluation()
    for upper, lower in _ADJACENT:
        upper_note, lower_note = voicing[upper], voicing[lower]
        if lower_note.midi > upper_note.midi:
            _add(result, _violation(
                profile, RuleCode.VOICE_CROSSING, "Voice crossing",
                f"{lower.value.title()} {lower_note.name} is above "
                f"{upper.value} {upper_note.name}.",
                slots=(slot_index,), voices=(upper, lower),
                notes=(upper_note.name, lower_note.name),
                correction=f"Place {upper.value} at or above {lower.value}.",
            ))
        elif lower_note.midi == upper_note.midi and not profile.permit_voice_unisons:
            _add(result, _violation(
                profile, RuleCode.FORBIDDEN_UNISON, "Voice unison is disabled",
                f"{upper.value.title()} and {lower.value} share {upper_note.name}.",
                slots=(slot_index,), voices=(upper, lower), notes=(upper_note.name,),
                correction="Separate the two voices under the selected profile.",
            ))
    for upper, lower in _ADJACENT[:2]:
        distance = voicing[upper].midi - voicing[lower].midi
        if distance > 12:
            _add(result, _violation(
                profile, RuleCode.UPPER_SPACING, "Upper voices too widely spaced",
                f"{upper.value.title()} and {lower.value} are {distance} semitones "
                "apart; the maximum is one octave.",
                slots=(slot_index,), voices=(upper, lower),
                notes=(voicing[upper].name, voicing[lower].name),
                correction=f"Move {upper.value} and {lower.value} within an octave.",
            ))
    tb = voicing.tenor.midi - voicing.bass.midi
    if tb > profile.max_tenor_bass_spacing:
        _add(result, _violation(
            profile, RuleCode.UPPER_SPACING, "Tenor-bass spacing is excessive",
            f"Tenor and bass are {tb} semitones apart; this profile permits "
            f"at most {profile.max_tenor_bass_spacing}.",
            slots=(slot_index,), voices=(Voice.TENOR, Voice.BASS),
            notes=(voicing.tenor.name, voicing.bass.name),
            correction="Bring tenor and bass closer together.",
        ))
    return result


def validate_chord(slot_index: int, problem: PartWritingProblem, voicing: Voicing,
                   harmony: NormalizedHarmony, profile: RuleProfile) -> RuleEvaluation:
    result = RuleEvaluation()
    slot = problem.slots[slot_index]
    for voice in VOICE_ORDER:
        note = voicing[voice]
        if _spelled_member_index(note, harmony) is None:
            pc_match = any(note.pc == member.pc for member in harmony.members)
            reason = ("uses an enharmonic spelling that does not match the chord"
                      if pc_match else "is not a member of the chord")
            _add(result, _violation(
                profile, RuleCode.CHORD_MEMBERSHIP, "Incorrect chord member",
                f"{voice.value.title()} {note.name} {reason} {harmony.label}.",
                slots=(slot_index,), voices=(voice,), notes=(note.name,),
                correction=f"Use a correctly spelled member of {harmony.label}.",
                field=f"slot.{slot_index}.{voice.value}",
            ))
        matches, reason = _constraint_matches(
            note, slot.voice(voice), harmony, problem.key_tonic, problem.mode)
        if not matches:
            _add(result, _violation(
                profile, RuleCode.REQUIRED_CONSTRAINT, "Locked constraint not satisfied",
                f"{voice.value.title()} {note.name} {reason}.",
                slots=(slot_index,), voices=(voice,), notes=(note.name,),
                correction=f"Honor the {voice.value} requirement or unlock that cell.",
                field=f"slot.{slot_index}.{voice.value}",
            ))

    expected_bass = harmony.members[harmony.inversion]
    if voicing.bass.name_no_octave != expected_bass.name_no_octave:
        _add(result, _violation(
            profile, RuleCode.INVERSION, "Bass contradicts the inversion",
            f"{harmony.label} requires {expected_bass.name_no_octave} in the bass, "
            f"but the bass is {voicing.bass.name}.",
            slots=(slot_index,), voices=(Voice.BASS,), notes=(voicing.bass.name,),
            correction=f"Put {expected_bass.name_no_octave} in the bass.",
            field=f"slot.{slot_index}.bass",
        ))
    exact_bass = slot.harmony.exact_bass_pitch
    if exact_bass is not None and voicing.bass != exact_bass:
        _add(result, _violation(
            profile, RuleCode.REQUIRED_CONSTRAINT, "Required bass pitch not satisfied",
            f"The bass must be exactly {exact_bass.name}, not {voicing.bass.name}.",
            slots=(slot_index,), voices=(Voice.BASS,), notes=(voicing.bass.name,),
            correction=f"Use {exact_bass.name} in the bass.",
            field=f"slot.{slot_index}.bass",
        ))

    counts = _factor_counts(voicing, harmony)
    required = set(harmony.factors)
    if len(harmony.factors) == 3 and profile.require_complete_triads:
        missing = required - set(counts)
        if missing:
            names = ", ".join(factor.value for factor in sorted(missing, key=lambda x: x.value))
            _add(result, _violation(
                profile, RuleCode.CHORD_COMPLETENESS, "Incomplete triad",
                f"{harmony.label} omits the chordal {names}.",
                slots=(slot_index,), notes=voicing.spelled_tuple,
                correction=f"Include the missing {names}.",
            ))
    elif len(harmony.factors) == 4:
        missing = required - set(counts)
        incomplete_v7 = (harmony.inversion == 0 and "V7" in harmony.label.upper()
                         and missing == {ChordFactor.FIFTH}
                         and counts[ChordFactor.ROOT] == 2
                         and profile.allow_incomplete_dominant_seventh)
        if missing and not incomplete_v7:
            names = ", ".join(factor.value for factor in sorted(missing, key=lambda x: x.value))
            _add(result, _violation(
                profile, RuleCode.CHORD_COMPLETENESS, "Incomplete seventh chord",
                f"{harmony.label} omits the chordal {names}.",
                slots=(slot_index,), notes=voicing.spelled_tuple,
                correction="Use all four chord members, or the documented incomplete V7 voicing.",
            ))

    required_doubling = slot.harmony.required_doubling
    if required_doubling is not None and counts[required_doubling] < 2:
        _add(result, _violation(
            profile, RuleCode.REQUIRED_DOUBLING, "Required doubling is absent",
            f"The chordal {required_doubling.value} must occur at least twice.",
            slots=(slot_index,), notes=voicing.spelled_tuple,
            correction=f"Double the chordal {required_doubling.value}.",
            field=f"slot.{slot_index}.required_doubling",
        ))

    for required_name in slot.harmony.required_chord_tones:
        if required_name.lower() in {factor.value for factor in ChordFactor}:
            factor = ChordFactor(required_name.lower())
            present = counts[factor] > 0
        else:
            present = any(note.name_no_octave == required_name for note in voicing.notes)
        if not present:
            _add(result, _violation(
                profile, RuleCode.REQUIRED_CONSTRAINT, "Required chord tone is absent",
                f"{required_name} is required in slot {slot_index + 1}.",
                slots=(slot_index,), correction=f"Add {required_name} to the voicing.",
                field=f"slot.{slot_index}.required_chord_tones",
            ))
    for forbidden_name in slot.harmony.forbidden_chord_tones:
        factor = None
        try:
            factor = ChordFactor(forbidden_name.lower())
        except ValueError:
            pass
        present = (counts[factor] > 0 if factor else
                   any(note.name_no_octave == forbidden_name for note in voicing.notes))
        if present:
            _add(result, _violation(
                profile, RuleCode.REQUIRED_CONSTRAINT, "Forbidden chord tone is present",
                f"{forbidden_name} is forbidden in slot {slot_index + 1}.",
                slots=(slot_index,), correction=f"Remove {forbidden_name} from the voicing.",
                field=f"slot.{slot_index}.forbidden_chord_tones",
            ))

    if counts[ChordFactor.SEVENTH] > 1:
        _add(result, _violation(
            profile, RuleCode.DOUBLED_CHORDAL_SEVENTH, "Doubled chordal seventh",
            f"{harmony.label} doubles its directed seventh.",
            slots=(slot_index,), notes=voicing.spelled_tuple,
            correction="Use one chordal seventh and redistribute another voice.",
        ))

    leading_pc = temporary_leading_tone_pc(harmony, problem.key_tonic, problem.mode)
    leading_voices = ([voice for voice in VOICE_ORDER if voicing[voice].pc == leading_pc]
                      if _dominant_context(harmony) else [])
    if len(leading_voices) > 1:
        _add(result, _violation(
            profile, RuleCode.DOUBLED_LEADING_TONE, "Doubled leading tone",
            "A leading tone is strongly directed and must not be doubled.",
            slots=(slot_index,), voices=leading_voices,
            notes=tuple(voicing[voice].name for voice in leading_voices),
            correction="Replace one leading tone with a stable chord member.",
        ))

    # Inversion-specific classroom doublings.
    if len(harmony.factors) == 3 and harmony.inversion == 2 \
            and counts[ChordFactor.FIFTH] < 2:
        _add(result, _violation(
            profile, RuleCode.REQUIRED_DOUBLING, "Second-inversion bass is not doubled",
            "A six-four chord normally doubles its bass, the chordal fifth.",
            slots=(slot_index,), notes=voicing.spelled_tuple,
            correction="Double the chordal fifth/bass.",
        ))
    if harmony.chord.quality == "diminished" and harmony.inversion == 1 \
            and counts[ChordFactor.THIRD] < 2:
        _add(result, _violation(
            profile, RuleCode.REQUIRED_DOUBLING,
            "First-inversion diminished-triad bass is not doubled",
            "A first-inversion diminished triad normally doubles its bass/chordal third.",
            slots=(slot_index,), notes=voicing.spelled_tuple,
            correction="Double the bass (the chordal third).",
        ))
    if harmony.special == "neapolitan" and counts[ChordFactor.THIRD] < 2:
        _add(result, _violation(
            profile, RuleCode.REQUIRED_DOUBLING, "Neapolitan bass is not doubled",
            "The Neapolitan normally appears in first inversion and doubles its bass/chordal third.",
            slots=(slot_index,), notes=voicing.spelled_tuple,
            correction="Double scale degree 4, the bass of N6.",
        ))
    if harmony.special == "augmented-sixth" and len(harmony.members) == 3 \
            and counts[ChordFactor.THIRD] < 2:
        _add(result, _violation(
            profile, RuleCode.REQUIRED_DOUBLING,
            "Italian augmented-sixth stable tone is not doubled",
            "The Italian augmented-sixth doubles tonic, not lowered 6 or raised 4.",
            slots=(slot_index,), notes=voicing.spelled_tuple,
            correction="Double tonic and keep one copy of each directed outer tone.",
        ))

    result.extend(_local_style(slot_index, voicing, harmony, profile))
    return result


def _motion(a: Note, b: Note) -> int:
    return (b.midi > a.midi) - (b.midi < a.midi)


def _interval_class(a: Note, b: Note) -> int:
    return abs(a.midi - b.midi) % 12


def _same_similar_motion(a1: Note, a2: Note, b1: Note, b2: Note) -> bool:
    ma, mb = _motion(a1, a2), _motion(b1, b2)
    return ma != 0 and ma == mb


def validate_voice_overlap(slot_index: int, previous: Voicing, current: Voicing,
                           profile: RuleProfile) -> RuleEvaluation:
    result = RuleEvaluation()
    for upper, lower in _ADJACENT:
        if current[lower].midi > previous[upper].midi:
            _add(result, _violation(
                profile, RuleCode.VOICE_OVERLAP, "Voice overlap",
                f"{lower.value.title()} moves above the previous {upper.value} note.",
                slots=(slot_index - 1, slot_index), voices=(upper, lower),
                notes=(previous[upper].name, current[lower].name),
                correction=f"Keep {lower.value} at or below the previous {upper.value}.",
            ))
        if current[upper].midi < previous[lower].midi:
            _add(result, _violation(
                profile, RuleCode.VOICE_OVERLAP, "Voice overlap",
                f"{upper.value.title()} moves below the previous {lower.value} note.",
                slots=(slot_index - 1, slot_index), voices=(upper, lower),
                notes=(previous[lower].name, current[upper].name),
                correction=f"Keep {upper.value} at or above the previous {lower.value}.",
            ))
    return result


def validate_parallel_and_direct_intervals(slot_index: int, previous: Voicing,
                                           current: Voicing,
                                           profile: RuleProfile) -> RuleEvaluation:
    result = RuleEvaluation()
    for upper, lower in _PAIRS:
        p1, p2 = previous[upper], current[upper]
        q1, q2 = previous[lower], current[lower]
        before, after = _interval_class(p1, q1), _interval_class(p2, q2)
        similar = _same_similar_motion(p1, p2, q1, q2)
        contrary = _motion(p1, p2) == -_motion(q1, q2) != 0
        compound = abs(p1.midi - q1.midi) > 12 or abs(p2.midi - q2.midi) > 12
        perfect_enabled = profile.treat_compound_perfects or not compound
        if perfect_enabled and similar and before == after == 7:
            _add(result, _violation(
                profile, RuleCode.PARALLEL_FIFTH, "Parallel perfect fifths",
                f"{upper.value.title()} and {lower.value} form consecutive perfect "
                "fifths by similar motion.",
                slots=(slot_index - 1, slot_index), voices=(upper, lower),
                notes=(p1.name, q1.name, p2.name, q2.name),
                correction="Retain a common tone or move one voice to another chord member.",
            ))
        if similar and before == after == 5:
            _add(result, _violation(
                profile, RuleCode.PARALLEL_FOURTH, "Parallel perfect fourths",
                f"{upper.value.title()} and {lower.value} form consecutive perfect fourths.",
                slots=(slot_index - 1, slot_index), voices=(upper, lower),
                notes=(p1.name, q1.name, p2.name, q2.name),
                correction="Use contrary or oblique motion under this profile.",
            ))
        if perfect_enabled and similar and before == after == 0:
            unison = (p1.midi == q1.midi and p2.midi == q2.midi)
            code = RuleCode.PARALLEL_UNISON if unison else RuleCode.PARALLEL_OCTAVE
            title = "Parallel unisons" if unison else "Parallel octaves"
            _add(result, _violation(
                profile, code, title,
                f"{upper.value.title()} and {lower.value} move through consecutive "
                f"{'unisons' if unison else 'octave-equivalent intervals'}.",
                slots=(slot_index - 1, slot_index), voices=(upper, lower),
                notes=(p1.name, q1.name, p2.name, q2.name),
                correction="Change one voice's destination while preserving the harmony.",
            ))
        if perfect_enabled and similar and before == after == 0 \
                and (p1.midi == q1.midi) != (p2.midi == q2.midi):
            _add(result, _violation(
                profile, RuleCode.PARALLEL_OCTAVE, "Unison-octave displacement",
                "Similar motion from a unison to an octave, or vice versa, is octave equivalence.",
                slots=(slot_index - 1, slot_index), voices=(upper, lower),
                notes=(p1.name, q1.name, p2.name, q2.name),
                correction="Change one voice's destination.",
            ))
        if perfect_enabled and contrary and before == after and after in (0, 7):
            _add(result, _violation(
                profile, RuleCode.ANTIPARALLEL_PERFECT,
                "Contrary perfect-interval displacement",
                "The selected profile treats octave-displaced contrary perfect intervals as parallels.",
                slots=(slot_index - 1, slot_index), voices=(upper, lower),
                notes=(p1.name, q1.name, p2.name, q2.name),
                correction="Choose a non-perfect destination interval.",
            ))
        if before == 6 and after == 7 and Voice.BASS in (upper, lower):
            _add(result, _violation(
                profile, RuleCode.UNEQUAL_FIFTH, "Unequal fifths",
                "A diminished fifth expands to a perfect fifth involving the bass.",
                slots=(slot_index - 1, slot_index), voices=(upper, lower),
                notes=(p1.name, q1.name, p2.name, q2.name),
                correction="Resolve the diminished fifth inward or choose a different voicing.",
            ))

    soprano_similar = _same_similar_motion(
        previous.soprano, current.soprano, previous.bass, current.bass)
    before_outer = _interval_class(previous.soprano, previous.bass)
    after_outer = _interval_class(current.soprano, current.bass)
    soprano_leaps = abs(current.soprano.diatonic_index - previous.soprano.diatonic_index) > 1
    direct = soprano_similar and after_outer in (0, 7) and before_outer != after_outer
    if direct and (soprano_leaps or profile.strict_hidden_perfects):
        code = RuleCode.HIDDEN_FIFTH if after_outer == 7 else RuleCode.HIDDEN_OCTAVE
        name = "fifth" if after_outer == 7 else "octave"
        _add(result, _violation(
            profile, code, f"Direct outer-voice {name}",
            f"Soprano and bass move similarly into a perfect {name} while the soprano leaps.",
            slots=(slot_index - 1, slot_index), voices=(Voice.SOPRANO, Voice.BASS),
            notes=(previous.soprano.name, previous.bass.name,
                   current.soprano.name, current.bass.name),
            correction="Let the soprano approach by step or use contrary/oblique motion.",
        ))
    return result


def _downward_step(previous: Note, current: Note) -> bool:
    return (previous.diatonic_index - current.diatonic_index == 1
            and previous.midi - current.midi in (1, 2))


def _upward_step(previous: Note, current: Note) -> bool:
    return (current.diatonic_index - previous.diatonic_index == 1
            and current.midi - previous.midi in (1, 2))


def _dominant_context(harmony: NormalizedHarmony) -> bool:
    label = harmony.label.replace("°", "o").replace("ø", "o")
    primary = label.split("/", 1)[0]
    return (bool(re.match(r"^V(?:7|65|43|42|2|6|64)?$", primary))
            or bool(re.match(r"^vii(?:o|o7|o65|o43|o42|6|7)?$", primary, re.IGNORECASE))
            or harmony.chord.quality in {"dom7", "dim7", "halfdim7"})


def validate_special_resolution(slot_index: int, problem: PartWritingProblem,
                                previous: Voicing, current: Voicing,
                                previous_harmony: NormalizedHarmony,
                                current_harmony: NormalizedHarmony,
                                profile: RuleProfile) -> RuleEvaluation:
    result = RuleEvaluation()
    previous_root_degree = scale_degree(
        previous_harmony.chord.root, problem.key_tonic, problem.mode)
    current_root_degree = scale_degree(
        current_harmony.chord.root, problem.key_tonic, problem.mode)
    slot = problem.slots[slot_index - 1]
    cadential_64 = (
        previous_harmony.inversion == 2 and previous_root_degree == 1
        and (slot.cadence_role.lower().replace("_", "-") in {"cadential", "cadential-64", "cadential-six-four"}
             or current_root_degree == 5)
    )
    if cadential_64:
        if current_root_degree != 5 or current.bass.pc != previous.bass.pc:
            _add(result, _violation(
                profile, RuleCode.CADENTIAL_SIX_FOUR,
                "Cadential six-four does not resolve to dominant",
                "A cadential I6/4 keeps scale degree 5 in the bass and resolves to V.",
                slots=(slot_index - 1, slot_index), voices=(Voice.BASS,),
                notes=(previous.bass.name, current.bass.name),
                correction="Keep scale degree 5 in the bass and resolve I6/4 to V.",
            ))
        for factor in (ChordFactor.ROOT, ChordFactor.THIRD):
            member = previous_harmony.member_for(factor)
            if member is None:
                continue
            for voice in VOICE_ORDER:
                if previous[voice].name_no_octave == member.name_no_octave \
                        and not _downward_step(previous[voice], current[voice]):
                    _add(result, _violation(
                        profile, RuleCode.CADENTIAL_SIX_FOUR,
                        "Cadential six-four suspension is unresolved",
                        "The sixth and fourth above the bass must resolve down to the fifth and third.",
                        slots=(slot_index - 1, slot_index), voices=(voice,),
                        notes=(previous[voice].name, current[voice].name),
                        correction="Resolve the cadential six-four tone downward by step.",
                    ))
    if previous_harmony.special == "neapolitan":
        lowered_two = previous_harmony.members[0]
        for voice in VOICE_ORDER:
            if previous[voice].name_no_octave == lowered_two.name_no_octave \
                    and not _downward_step(previous[voice], current[voice]):
                _add(result, _violation(
                    profile, RuleCode.LEADING_TONE_RESOLUTION,
                    "Neapolitan lowered second is unresolved",
                    "Lowered scale degree 2 normally descends by step toward dominant harmony.",
                    slots=(slot_index - 1, slot_index), voices=(voice,),
                    notes=(previous[voice].name, current[voice].name),
                    correction="Move lowered scale degree 2 downward by step.",
                ))
    return result


def validate_tendency_tones(slot_index: int, problem: PartWritingProblem,
                            previous: Voicing, current: Voicing,
                            previous_harmony: NormalizedHarmony,
                            profile: RuleProfile) -> RuleEvaluation:
    result = RuleEvaluation()
    if _dominant_context(previous_harmony):
        target_pc = (previous_harmony.applied_target_pc
                     if previous_harmony.applied_target_pc is not None
                     else tonic_pc(problem.key_tonic))
        leading_pc = (target_pc - 1) % 12
        for voice in VOICE_ORDER:
            if previous[voice].pc != leading_pc:
                continue
            resolved = current[voice].pc == target_pc and _upward_step(previous[voice], current[voice])
            inner_exception = (
                profile.inner_leading_tone_exception
                and voice in (Voice.ALTO, Voice.TENOR)
                and current[voice].pc == (target_pc + 7) % 12
                and current[voice].midi < previous[voice].midi
            )
            if not (resolved or inner_exception):
                _add(result, _violation(
                    profile, RuleCode.LEADING_TONE_RESOLUTION,
                    "Unresolved leading tone",
                    f"{voice.value.title()} {previous[voice].name} must resolve upward "
                    "by a spelled step to its tonic.",
                    slots=(slot_index - 1, slot_index), voices=(voice,),
                    notes=(previous[voice].name, current[voice].name),
                    correction="Resolve the leading tone upward by step.",
                ))
    seventh = previous_harmony.member_for(ChordFactor.SEVENTH)
    if seventh is not None:
        for voice in VOICE_ORDER:
            if previous[voice].name_no_octave == seventh.name_no_octave \
                    and not _downward_step(previous[voice], current[voice]):
                _add(result, _violation(
                    profile, RuleCode.CHORDAL_SEVENTH_RESOLUTION,
                    "Unresolved chordal seventh",
                    f"The seventh in {voice.value} normally resolves downward by step.",
                    slots=(slot_index - 1, slot_index), voices=(voice,),
                    notes=(previous[voice].name, current[voice].name),
                    correction="Move the chordal seventh down by a spelled step.",
                ))

    if previous_harmony.special == "augmented-sixth":
        dominant_pc = (tonic_pc(problem.key_tonic) + 7) % 12
        low = previous_harmony.members[0]
        high = previous_harmony.members[-1]
        for voice in VOICE_ORDER:
            if previous[voice].name_no_octave == low.name_no_octave:
                if not (current[voice].pc == dominant_pc and current[voice].midi < previous[voice].midi):
                    _add(result, _violation(
                        profile, RuleCode.AUGMENTED_SIXTH_RESOLUTION,
                        "Lower augmented-sixth tendency did not resolve outward",
                        "Lowered scale degree 6 must move down to the dominant.",
                        slots=(slot_index - 1, slot_index), voices=(voice,),
                        notes=(previous[voice].name, current[voice].name),
                        correction="Resolve lowered 6 down to scale degree 5.",
                    ))
            if previous[voice].name_no_octave == high.name_no_octave:
                if not (current[voice].pc == dominant_pc and current[voice].midi > previous[voice].midi):
                    _add(result, _violation(
                        profile, RuleCode.AUGMENTED_SIXTH_RESOLUTION,
                        "Upper augmented-sixth tendency did not resolve outward",
                        "Raised scale degree 4 must move up to the dominant.",
                        slots=(slot_index - 1, slot_index), voices=(voice,),
                        notes=(previous[voice].name, current[voice].name),
                        correction="Resolve raised 4 up to scale degree 5.",
                    ))
    return result


def validate_melodic_intervals(slot_index: int, previous: Voicing, current: Voicing,
                               profile: RuleProfile) -> RuleEvaluation:
    result = RuleEvaluation()
    for voice in VOICE_ORDER:
        first, second = previous[voice], current[voice]
        interval = interval_between(first, second)
        distance = abs(second.midi - first.midi)
        if distance == 0:
            continue
        if interval.quality.startswith("A"):
            _add(result, _violation(
                profile, RuleCode.MELODIC_AUGMENTED, "Augmented melodic interval",
                f"{voice.value.title()} moves by {interval.name} from {first.name} to {second.name}.",
                slots=(slot_index - 1, slot_index), voices=(voice,),
                notes=(first.name, second.name), correction="Respell or replace the leap with singable motion.",
            ))
        if interval.quality.startswith("d"):
            _add(result, _violation(
                profile, RuleCode.MELODIC_DIMINISHED, "Diminished melodic interval",
                f"{voice.value.title()} moves by {interval.name}.",
                slots=(slot_index - 1, slot_index), voices=(voice,),
                notes=(first.name, second.name), correction="Prefer a diatonic step or consonant leap.",
            ))
        simple_number = ((interval.number - 1) % 7) + 1
        if simple_number == 7:
            _add(result, _violation(
                profile, RuleCode.MELODIC_SEVENTH, "Melodic seventh",
                f"{voice.value.title()} leaps a seventh from {first.name} to {second.name}.",
                slots=(slot_index - 1, slot_index), voices=(voice,),
                notes=(first.name, second.name), correction="Use a smaller melodic interval.",
            ))
        if distance > profile.max_melodic_leap and distance != 12:
            _add(result, _violation(
                profile, RuleCode.MELODIC_LARGE_LEAP, "Excessive melodic leap",
                f"{voice.value.title()} leaps {distance} semitones; this profile permits "
                f"at most {profile.max_melodic_leap}, except an octave.",
                slots=(slot_index - 1, slot_index), voices=(voice,),
                notes=(first.name, second.name), correction="Choose a nearer chord member.",
            ))
    return result


def validate_three_event_melody(slot_index: int, first: Voicing, second: Voicing,
                                third: Voicing, profile: RuleProfile) -> RuleEvaluation:
    result = RuleEvaluation()
    for voice in VOICE_ORDER:
        a, b, c = first[voice], second[voice], third[voice]
        d1, d2 = b.midi - a.midi, c.midi - b.midi
        if abs(d1) > profile.large_leap_threshold:
            recovered = d1 * d2 < 0 and abs(c.diatonic_index - b.diatonic_index) == 1
            if not recovered:
                _add(result, _violation(
                    profile, RuleCode.MELODIC_LEAP_RECOVERY,
                    "Large leap is not recovered",
                    f"After a {abs(d1)}-semitone leap, {voice.value} should reverse direction by step.",
                    slots=(slot_index - 2, slot_index - 1, slot_index), voices=(voice,),
                    notes=(a.name, b.name, c.name),
                    correction="Follow the leap with stepwise motion in the opposite direction.",
                ))
        if abs(d1) > 2 and abs(d2) > 2:
            info = identify_chord([a, b, c])
            if info is None:
                _add(result, _violation(
                    profile, RuleCode.CONSECUTIVE_LEAPS,
                    "Consecutive leaps do not outline a triad",
                    f"{voice.value.title()} makes successive leaps through "
                    f"{a.name}, {b.name}, {c.name} without outlining a recognizable triad.",
                    slots=(slot_index - 2, slot_index - 1, slot_index), voices=(voice,),
                    notes=(a.name, b.name, c.name),
                    correction="Use stepwise motion or outline a clear triad.",
                ))
    return result


def validate_transition(slot_index: int, problem: PartWritingProblem,
                        previous: Voicing, current: Voicing,
                        previous_harmony: NormalizedHarmony,
                        current_harmony: NormalizedHarmony,
                        profile: RuleProfile) -> RuleEvaluation:
    result = RuleEvaluation()
    result.extend(validate_voice_overlap(slot_index, previous, current, profile))
    result.extend(validate_parallel_and_direct_intervals(slot_index, previous, current, profile))
    result.extend(validate_tendency_tones(
        slot_index, problem, previous, current, previous_harmony, profile))
    result.extend(validate_special_resolution(
        slot_index, problem, previous, current, previous_harmony,
        current_harmony, profile))
    result.extend(validate_melodic_intervals(slot_index, previous, current, profile))
    result.extend(_transition_style(previous, current, profile))
    return result


def validate_local(slot_index: int, problem: PartWritingProblem, voicing: Voicing,
                   harmony: NormalizedHarmony, profile: RuleProfile) -> RuleEvaluation:
    result = RuleEvaluation()
    result.extend(validate_voice_ranges(slot_index, voicing, profile))
    result.extend(validate_voice_order_and_spacing(slot_index, voicing, profile))
    result.extend(validate_chord(slot_index, problem, voicing, harmony, profile))
    return result


def _root_degree(harmony: NormalizedHarmony, problem: PartWritingProblem) -> int | None:
    return scale_degree(harmony.chord.root, problem.key_tonic, problem.mode)


def validate_cadence(problem: PartWritingProblem, harmonies: list[NormalizedHarmony],
                     voicings: list[Voicing], profile: RuleProfile) -> RuleEvaluation:
    result = RuleEvaluation()
    if problem.cadence is None or not harmonies or not voicings:
        return result
    final_degree = _root_degree(harmonies[-1], problem)
    previous_degree = _root_degree(harmonies[-2], problem) if len(harmonies) >= 2 else None
    final_bass_degree = scale_degree(voicings[-1].bass, problem.key_tonic, problem.mode)
    final_soprano_degree = scale_degree(voicings[-1].soprano, problem.key_tonic, problem.mode)
    previous_bass_degree = (scale_degree(voicings[-2].bass, problem.key_tonic, problem.mode)
                            if len(voicings) >= 2 else None)
    ok = True
    expectation = ""
    cadence = problem.cadence
    if cadence == CadenceType.PERFECT_AUTHENTIC:
        ok = (previous_degree == 5 and final_degree == 1
              and previous_bass_degree == 5 and final_bass_degree == 1
              and final_soprano_degree == 1
              and harmonies[-2].inversion == harmonies[-1].inversion == 0)
        expectation = "root-position V-I with scale degree 1 in the final soprano"
    elif cadence == CadenceType.IMPERFECT_AUTHENTIC:
        ok = previous_degree == 5 and final_degree == 1
        expectation = "a dominant-to-tonic ending that is not a perfect authentic cadence"
        if ok and final_soprano_degree == 1 and harmonies[-2].inversion == harmonies[-1].inversion == 0:
            ok = False
    elif cadence == CadenceType.HALF:
        ok = final_degree == 5 and harmonies[-1].inversion == 0
        expectation = "a root-position dominant final harmony"
    elif cadence == CadenceType.DECEPTIVE:
        ok = (previous_degree == 5 and final_degree == 6
              and previous_bass_degree == 5 and final_bass_degree == 6)
        expectation = "V-vi in major or V-VI in minor, with bass scale degrees 5-6"
    elif cadence == CadenceType.PLAGAL:
        ok = previous_degree == 4 and final_degree == 1
        expectation = "IV-I (or iv-i)"
    if not ok:
        _add(result, _violation(
            profile, RuleCode.CADENCE, "Cadence requirement is not met",
            f"A {cadence.value.replace('-', ' ')} cadence requires {expectation}.",
            slots=tuple(range(max(0, len(voicings) - 2), len(voicings))),
            notes=tuple(note.name for voicing in voicings[-2:] for note in voicing.notes),
            correction="Adjust the final harmonies, bass, or soprano to match the requested cadence.",
            field="cadence",
        ))
    return result


def _local_style(slot_index: int, voicing: Voicing, harmony: NormalizedHarmony,
                 profile: RuleProfile) -> RuleEvaluation:
    result = RuleEvaluation()
    counts = _factor_counts(voicing, harmony)
    if len(harmony.factors) == 3 and harmony.inversion == 0:
        if counts[ChordFactor.ROOT] >= 2:
            value = profile.weights.get("root_doubling", -1.0)
            result.soft_score += value
            result.score_breakdown["Root doubling"] = value
        else:
            value = abs(profile.weights.get("incomplete_chord", 2.0))
            result.soft_score += value
            result.score_breakdown["Nonstandard root-position doubling"] = value
    for voice in VOICE_ORDER:
        rng = profile.voice_ranges[voice]
        distance = min(voicing[voice].midi - rng.minimum.midi,
                       rng.maximum.midi - voicing[voice].midi)
        if distance <= 1:
            value = profile.weights.get("range_extreme", 2.0)
            result.soft_score += value
            result.score_breakdown[f"{voice.value.title()} range extreme"] = value
    upper_spacing = (voicing.soprano.midi - voicing.alto.midi
                     + voicing.alto.midi - voicing.tenor.midi)
    spacing_value = profile.weights.get("balanced_spacing", 0.25) * abs(14 - upper_spacing)
    result.soft_score += spacing_value
    result.score_breakdown[f"Slot {slot_index + 1} spacing"] = spacing_value
    return result


def _transition_style(previous: Voicing, current: Voicing,
                      profile: RuleProfile) -> RuleEvaluation:
    result = RuleEvaluation()
    motions = {voice: current[voice].midi - previous[voice].midi for voice in VOICE_ORDER}
    total = sum(abs(value) for value in motions.values()) * profile.weights.get("total_motion", 1.0)
    result.soft_score += total
    result.score_breakdown["Total semitone motion"] = total
    common = sum(value == 0 for value in motions.values())
    common_value = common * profile.weights.get("common_tone", -2.5)
    result.soft_score += common_value
    result.score_breakdown["Retained common tones"] = common_value
    steps = sum(0 < abs(motions[voice]) <= 2 for voice in VOICE_ORDER[:3])
    step_value = steps * profile.weights.get("stepwise_upper", -1.5)
    result.soft_score += step_value
    result.score_breakdown["Stepwise upper voices"] = step_value
    bass_motion = motions[Voice.BASS]
    contrary = sum(value * bass_motion < 0 for voice, value in motions.items()
                   if voice != Voice.BASS and value)
    contrary_value = contrary * profile.weights.get("contrary_bass", -1.0)
    result.soft_score += contrary_value
    result.score_breakdown["Contrary motion with bass"] = contrary_value
    nonzero = [value for value in motions.values() if value]
    if len(nonzero) == 4 and all(value > 0 for value in nonzero) \
            or len(nonzero) == 4 and all(value < 0 for value in nonzero):
        value = profile.weights.get("all_similar", 4.0)
        result.soft_score += value
        result.score_breakdown["All voices in similar motion"] = value
    if motions[Voice.SOPRANO] == 0:
        value = profile.weights.get("repeated_soprano", 0.75)
        result.soft_score += value
        result.score_breakdown["Repeated soprano"] = value
    if abs(motions[Voice.SOPRANO]) > 5:
        value = profile.weights.get("large_soprano_leap", 3.0)
        result.soft_score += value
        result.score_breakdown["Large soprano leap"] = value
    return result


def evaluate_solution(problem: PartWritingProblem, harmonies: list[NormalizedHarmony],
                      voicings: list[Voicing], profile: RuleProfile) -> RuleEvaluation:
    result = RuleEvaluation()
    for index, (voicing, harmony) in enumerate(zip(voicings, harmonies)):
        result.extend(validate_local(index, problem, voicing, harmony, profile))
        if index:
            result.extend(validate_transition(
                index, problem, voicings[index - 1], voicing,
                harmonies[index - 1], harmony, profile))
        if index >= 2:
            result.extend(validate_three_event_melody(
                index, voicings[index - 2], voicings[index - 1], voicing, profile))
    result.extend(validate_cadence(problem, harmonies, voicings, profile))
    return result
