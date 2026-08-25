"""Validated, reproducible practice generation built on the real solver."""

from __future__ import annotations

import copy
import random
from dataclasses import dataclass
from enum import Enum

from .diagnostics import check_solution
from .models import (
    CadenceType, HarmonyConstraint, HarmonySlot, PartWritingProblem,
    PartWritingSolution, SolverOptions, Voice, VOICE_ORDER,
)
from .profiles import RuleProfile, profile_for
from .solver import solve


class PracticeType(str, Enum):
    FILL_INNER_VOICE = "fill-inner-voice"
    FILL_BOTH_INNER = "fill-both-inner-voices"
    COMPLETE_CHORD = "complete-one-chord"
    COMPLETE_CADENCE = "complete-cadence"
    FIGURED_BASS = "realize-figured-bass"
    ROMAN_PROGRESS = "realize-roman-progression"
    ABOVE_BASS = "add-upper-voices"
    BELOW_SOPRANO = "add-lower-voices"
    PARTIAL_SCORE = "partial-satb-score"
    SOPRANO_LINE = "create-soprano-line"
    BASS_LINE = "create-bass-line"
    CHROMATIC = "chromatic-harmony"


@dataclass
class GeneratedPractice:
    problem: PartWritingProblem
    answer: PartWritingSolution
    practice_type: PracticeType
    unique: bool
    seed: int
    instructions: str


_MAJOR_TEMPLATES = (
    (("I", "IV", "V", "I"), CadenceType.PERFECT_AUTHENTIC),
    (("I", "ii6", "V7", "I"), CadenceType.PERFECT_AUTHENTIC),
    (("I", "vi", "ii6", "V", "I"), CadenceType.PERFECT_AUTHENTIC),
    (("I", "IV", "V", "vi"), CadenceType.DECEPTIVE),
    (("I", "V6", "vi", "IV", "V", "I"), CadenceType.PERFECT_AUTHENTIC),
)
_MINOR_TEMPLATES = (
    (("i", "iv", "V", "i"), CadenceType.PERFECT_AUTHENTIC),
    (("i", "iio6", "V7", "i"), CadenceType.PERFECT_AUTHENTIC),
    (("i", "VI", "iv", "V", "i"), CadenceType.PERFECT_AUTHENTIC),
    (("i", "iv", "V", "VI"), CadenceType.DECEPTIVE),
)
_CHROMATIC_TEMPLATES = (
    (("I", "V/V", "V", "I"), CadenceType.PERFECT_AUTHENTIC, "major"),
    (("i", "N6", "V", "i"), CadenceType.PERFECT_AUTHENTIC, "minor"),
    (("I", "bVI", "V", "I"), CadenceType.PERFECT_AUTHENTIC, "major"),
)


def _figured(label: str) -> str:
    if label.endswith("64"):
        return "64"
    if label.endswith("65"):
        return "65"
    if label.endswith("43"):
        return "43"
    if label.endswith("42"):
        return "42"
    if label.endswith("7"):
        return "7"
    if label.endswith("6"):
        return "6"
    return ""


def _base_problem(difficulty: float, rng: random.Random,
                  practice_type: PracticeType, profile: RuleProfile) -> PartWritingProblem:
    chromatic = practice_type == PracticeType.CHROMATIC or difficulty >= 8.5
    if chromatic:
        labels, cadence, mode = rng.choice(_CHROMATIC_TEMPLATES)
    else:
        mode = "minor" if difficulty >= 5 and rng.random() < 0.38 else "major"
        labels, cadence = rng.choice(_MINOR_TEMPLATES if mode == "minor" else _MAJOR_TEMPLATES)
    max_slots = 4 if difficulty < 3 else 5 if difficulty < 6 else len(labels)
    labels = labels[:max_slots]
    # Preserve the template's cadential ending when shortening.
    if len(labels) < 2 or labels[-1].lower().rstrip("7") not in {"i", "vi"}:
        cadence = None
    tonic_choices = (["C", "G", "F"] if difficulty < 4 else
                     ["C", "G", "D", "F", "Bb", "A", "Eb"])
    tonic = rng.choice(tonic_choices)
    slots = [HarmonySlot(HarmonyConstraint(roman_numeral=label), duration=1.0)
             for label in labels]
    return PartWritingProblem(
        key_tonic=tonic, mode=mode, meter=(4, 4), slots=slots,
        cadence=cadence, profile_id=profile.id, tempo=76 + int(difficulty * 2),
        title=f"{tonic} {mode} SATB practice", seed=rng.randrange(2**31),
    )


def _lock(slot: HarmonySlot, voice: Voice, answer_note) -> None:
    constraint = slot.voice(voice)
    constraint.pitch.exact = answer_note
    constraint.locked = True


def _apply_mask(problem: PartWritingProblem, answer: PartWritingSolution,
                practice_type: PracticeType, difficulty: float,
                rng: random.Random) -> str:
    if practice_type == PracticeType.FILL_INNER_VOICE:
        missing = rng.choice((Voice.ALTO, Voice.TENOR))
        for slot, voicing in zip(problem.slots, answer.voicings):
            for voice in VOICE_ORDER:
                if voice != missing:
                    _lock(slot, voice, voicing[voice])
        return f"Write the {missing.value} while preserving every locked note."
    if practice_type == PracticeType.FILL_BOTH_INNER:
        for slot, voicing in zip(problem.slots, answer.voicings):
            _lock(slot, Voice.SOPRANO, voicing.soprano)
            _lock(slot, Voice.BASS, voicing.bass)
        return "Complete alto and tenor between the supplied outer voices."
    if practice_type == PracticeType.COMPLETE_CHORD:
        target = rng.randrange(len(problem.slots))
        for index, (slot, voicing) in enumerate(zip(problem.slots, answer.voicings)):
            for voice in VOICE_ORDER:
                if index != target or voice in (Voice.SOPRANO, Voice.BASS):
                    _lock(slot, voice, voicing[voice])
        return f"Complete chord {target + 1}; the surrounding progression is locked."
    if practice_type == PracticeType.COMPLETE_CADENCE:
        cutoff = max(0, len(problem.slots) - 2)
        for index, (slot, voicing) in enumerate(zip(problem.slots, answer.voicings)):
            if index < cutoff:
                for voice in VOICE_ORDER:
                    _lock(slot, voice, voicing[voice])
            else:
                _lock(slot, Voice.BASS, voicing.bass)
        return f"Complete the requested {problem.cadence.value if problem.cadence else 'phrase'} ending."
    if practice_type in (PracticeType.FIGURED_BASS, PracticeType.ABOVE_BASS,
                         PracticeType.BASS_LINE):
        for slot, voicing in zip(problem.slots, answer.voicings):
            _lock(slot, Voice.BASS, voicing.bass)
            if practice_type == PracticeType.FIGURED_BASS:
                slot.harmony.figured_bass = _figured(slot.harmony.roman_numeral or "")
        if practice_type == PracticeType.BASS_LINE:
            # A bass-line exercise supplies the upper voices instead.
            for slot, voicing in zip(problem.slots, answer.voicings):
                slot.voice(Voice.BASS).pitch.exact = None
                slot.voice(Voice.BASS).locked = False
                for voice in (Voice.SOPRANO, Voice.ALTO, Voice.TENOR):
                    _lock(slot, voice, voicing[voice])
            return "Create a bass line under the locked upper voices."
        return "Realize the progression above the locked figured bass."
    if practice_type in (PracticeType.BELOW_SOPRANO, PracticeType.SOPRANO_LINE):
        for slot, voicing in zip(problem.slots, answer.voicings):
            _lock(slot, Voice.SOPRANO, voicing.soprano)
        if practice_type == PracticeType.SOPRANO_LINE:
            for slot, voicing in zip(problem.slots, answer.voicings):
                slot.voice(Voice.SOPRANO).pitch.exact = None
                slot.voice(Voice.SOPRANO).locked = False
                for voice in (Voice.ALTO, Voice.TENOR, Voice.BASS):
                    _lock(slot, voice, voicing[voice])
            return "Create a singable soprano over the locked lower voices."
        return "Add alto, tenor, and bass below the locked soprano."
    if practice_type == PracticeType.PARTIAL_SCORE:
        lock_probability = max(0.2, 0.7 - difficulty * 0.05)
        for slot, voicing in zip(problem.slots, answer.voicings):
            for voice in VOICE_ORDER:
                if rng.random() < lock_probability:
                    _lock(slot, voice, voicing[voice])
        return "Complete every blank cell; locked clues may not be changed."
    return "Realize the supplied Roman-numeral progression in valid SATB style."


def _restore_uniqueness(problem: PartWritingProblem, answer: PartWritingSolution,
                        profile: RuleProfile, rng: random.Random) -> bool:
    for _ in range(len(problem.slots) * 4 + 1):
        result = solve(problem, profile, SolverOptions(top_k=2, time_limit_seconds=8,
                                                       max_nodes=180_000))
        if len(result.solutions) == 1:
            return True
        if not result.solutions:
            return False
        alternatives = result.solutions[1:]
        choices = []
        for slot_index, (slot, expected) in enumerate(zip(problem.slots, answer.voicings)):
            for voice in VOICE_ORDER:
                if slot.voice(voice).locked:
                    continue
                if any(alt.voicings[slot_index][voice] != expected[voice]
                       for alt in alternatives):
                    choices.append((slot_index, voice))
        if not choices:
            return False
        slot_index, voice = rng.choice(choices)
        _lock(problem.slots[slot_index], voice, answer.voicings[slot_index][voice])
    return False


def generate_practice(difficulty: float = 5.0, rng: random.Random | None = None,
                      practice_type: PracticeType = PracticeType.PARTIAL_SCORE,
                      *, require_unique: bool = False,
                      profile: RuleProfile | None = None) -> GeneratedPractice:
    rng = rng or random.Random()
    difficulty = max(0.0, min(10.0, float(difficulty)))
    profile = profile or profile_for("common-practice")
    for _attempt in range(12):
        complete = _base_problem(difficulty, rng, practice_type, profile)
        result = solve(complete, profile, SolverOptions(top_k=1, time_limit_seconds=8,
                                                        max_nodes=200_000))
        if not result.solutions:
            continue
        answer = result.solutions[0]
        masked = copy.deepcopy(complete)
        instructions = _apply_mask(masked, answer, practice_type, difficulty, rng)
        uniqueness = False
        if require_unique:
            uniqueness = _restore_uniqueness(masked, answer, profile, rng)
            if not uniqueness:
                continue
        else:
            validation = solve(masked, profile, SolverOptions(top_k=1,
                                                               time_limit_seconds=8,
                                                               max_nodes=200_000))
            if not validation.solutions:
                continue
        return GeneratedPractice(masked, answer, practice_type, uniqueness,
                                 complete.seed, instructions)
    raise RuntimeError("Unable to generate a validated part-writing exercise")


def grade_practice(practice: GeneratedPractice, voicings) -> bool:
    evaluation = check_solution(practice.problem, list(voicings),
                                profile_for(practice.problem.profile_id))
    return not evaluation.hard_violations
