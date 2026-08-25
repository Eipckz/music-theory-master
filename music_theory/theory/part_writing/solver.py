"""Exact, deterministic graph search for top-ranked SATB solutions."""

from __future__ import annotations

import time
import copy
from collections import Counter, defaultdict
from dataclasses import dataclass

from .diagnostics import no_solution_diagnostics, preflight_diagnostics
from .harmony import NormalizedHarmony, harmonies_for_slot
from .models import (
    PartWritingProblem, PartWritingSolution, RuleCode, RuleEvaluation,
    RuleViolation, SolveResult, SolveStatistics, SolveStatus, SolverOptions,
    VOICE_ORDER, Voicing,
)
from .profiles import RuleProfile, profile_for
from .rules import (
    evaluate_solution, validate_cadence, validate_three_event_melody,
    validate_transition,
)
from .voicings import CandidateVoicing, enumerate_voicings


@dataclass(frozen=True)
class _SlotCandidate:
    harmony: NormalizedHarmony
    candidate: CandidateVoicing

    @property
    def voicing(self) -> Voicing:
        return self.candidate.voicing

    @property
    def signature(self) -> tuple:
        return self.harmony.label, self.voicing.spelled_tuple


@dataclass
class _Path:
    nodes: tuple[_SlotCandidate, ...]
    score: float
    breakdown: dict[str, float]

    @property
    def tie_key(self) -> tuple:
        return tuple(node.signature for node in self.nodes)


class _LimitReached(Exception):
    pass


class _Cancelled(Exception):
    pass


def _merge_breakdown(base: dict[str, float], extra: dict[str, float],
                     *, prefix: str = "") -> dict[str, float]:
    out = dict(base)
    for key, value in extra.items():
        name = f"{prefix}{key}" if prefix else key
        out[name] = out.get(name, 0.0) + value
    return out


def _check_limits(options: SolverOptions, statistics: SolveStatistics,
                  started: float) -> None:
    if options.cancellation is not None and options.cancellation.is_set():
        raise _Cancelled
    if statistics.nodes_visited >= options.max_nodes:
        raise _LimitReached
    if time.perf_counter() - started >= options.time_limit_seconds:
        raise _LimitReached


def _record_rejections(evaluation: RuleEvaluation, counts: Counter,
                       samples: dict[RuleCode, RuleViolation]) -> None:
    for violation in evaluation.hard_violations:
        counts[violation.code] += 1
        samples.setdefault(violation.code, violation)


def _slot_candidates(problem: PartWritingProblem, profile: RuleProfile,
                     statistics: SolveStatistics) -> tuple[list[list[_SlotCandidate]], list[int]]:
    all_slots: list[list[_SlotCandidate]] = []
    empty_slots = []
    for index in range(len(problem.slots)):
        slot_candidates = []
        harmonies = harmonies_for_slot(problem, index)
        for harmony in harmonies:
            for candidate in enumerate_voicings(problem, index, harmony, profile, maximum=600):
                slot_candidates.append(_SlotCandidate(harmony, candidate))
        # Same voicing can be reachable through equivalent user alternatives;
        # keep the label in identity so genuinely different analyses remain visible.
        unique = {candidate.signature: candidate for candidate in slot_candidates}
        ordered = sorted(unique.values(), key=lambda item: (
            round(item.candidate.local_score, 8), item.signature))
        statistics.local_candidates += len(ordered)
        all_slots.append(ordered)
        if not ordered:
            empty_slots.append(index)
    return all_slots, empty_slots


def solve(problem: PartWritingProblem, profile: RuleProfile | None = None,
          options: SolverOptions | None = None) -> SolveResult:
    """Return up to ``top_k`` valid solutions, or an honest terminal status."""
    profile = profile or profile_for(problem.profile_id)
    options = (options or SolverOptions()).normalized()
    statistics = SolveStatistics()
    started = time.perf_counter()
    preflight = preflight_diagnostics(problem, profile)
    if preflight:
        statistics.elapsed_seconds = time.perf_counter() - started
        return SolveResult(SolveStatus.INVALID_INPUT, diagnostics=preflight,
                           statistics=statistics, message="Input constraints conflict.")
    if options.cancellation is not None and options.cancellation.is_set():
        statistics.elapsed_seconds = time.perf_counter() - started
        return SolveResult(SolveStatus.CANCELLED, statistics=statistics,
                           message="The search was cancelled by the user.")
    try:
        slots, empty_slots = _slot_candidates(problem, profile, statistics)
    except ValueError as exc:
        statistics.elapsed_seconds = time.perf_counter() - started
        violation = RuleViolation(
            RuleCode.HARMONY_LABEL_CONFLICT, profile.severity(RuleCode.HARMONY_LABEL_CONFLICT),
            "Harmony cannot be normalized", str(exc), correction="Correct the harmony label.")
        return SolveResult(SolveStatus.INVALID_INPUT, diagnostics=[violation],
                           statistics=statistics, message=str(exc))
    if empty_slots:
        statistics.elapsed_seconds = time.perf_counter() - started
        diagnostics = no_solution_diagnostics(
            problem, profile, empty_slots, Counter(), {})
        return SolveResult(SolveStatus.NO_SOLUTION, diagnostics=diagnostics,
                           statistics=statistics,
                           message="One or more slots have no legal local voicing.")

    rejection_counts: Counter = Counter()
    rejection_samples: dict[RuleCode, RuleViolation] = {}
    transition_cache: dict[tuple, RuleEvaluation] = {}
    three_cache: dict[tuple, RuleEvaluation] = {}
    try:
        states: dict[tuple, list[_Path]] = {}
        for candidate in slots[0]:
            breakdown = dict(candidate.candidate.breakdown)
            path = _Path((candidate,), candidate.candidate.local_score, breakdown)
            states.setdefault((candidate.signature,), []).append(path)

        for slot_index in range(1, len(slots)):
            next_states: dict[tuple, list[_Path]] = defaultdict(list)
            for paths in states.values():
                for path in paths:
                    previous = path.nodes[-1]
                    for current in slots[slot_index]:
                        _check_limits(options, statistics, started)
                        statistics.nodes_visited += 1
                        statistics.transitions_checked += 1
                        transition_key = (slot_index, previous.signature, current.signature)
                        evaluation = transition_cache.get(transition_key)
                        if evaluation is None:
                            evaluation = validate_transition(
                                slot_index, problem, previous.voicing, current.voicing,
                                previous.harmony, current.harmony, profile)
                            transition_cache[transition_key] = evaluation
                        if evaluation.hard_violations:
                            statistics.rejected_transitions += 1
                            _record_rejections(evaluation, rejection_counts, rejection_samples)
                            continue
                        three = RuleEvaluation()
                        if slot_index >= 2:
                            first = path.nodes[-2]
                            three_key = (slot_index, first.signature,
                                         previous.signature, current.signature)
                            cached_three = three_cache.get(three_key)
                            if cached_three is None:
                                cached_three = validate_three_event_melody(
                                    slot_index, first.voicing, previous.voicing,
                                    current.voicing, profile)
                                three_cache[three_key] = cached_three
                            three = cached_three
                            if three.hard_violations:
                                statistics.rejected_transitions += 1
                                _record_rejections(three, rejection_counts, rejection_samples)
                                continue
                        score = (path.score + current.candidate.local_score
                                 + evaluation.soft_score + three.soft_score)
                        breakdown = _merge_breakdown(path.breakdown,
                                                     dict(current.candidate.breakdown),
                                                     prefix=f"Slot {slot_index + 1}: ")
                        breakdown = _merge_breakdown(
                            breakdown, evaluation.score_breakdown,
                            prefix=f"Transition {slot_index}-{slot_index + 1}: ")
                        breakdown = _merge_breakdown(
                            breakdown, three.score_breakdown,
                            prefix=f"Slots {slot_index - 1}-{slot_index + 1}: ")
                        new_path = _Path(path.nodes + (current,), score, breakdown)
                        key = (previous.signature, current.signature)
                        bucket = next_states[key]
                        bucket.append(new_path)
                        bucket.sort(key=lambda item: (round(item.score, 8), item.tie_key))
                        if len(bucket) > options.top_k:
                            del bucket[options.top_k:]
            states = dict(next_states)
            if options.progress_callback is not None:
                try:
                    options.progress_callback(slot_index + 1, len(problem.slots))
                except Exception:  # noqa: BLE001 - progress reporting cannot break solving
                    pass
            if not states:
                break
    except _Cancelled:
        statistics.elapsed_seconds = time.perf_counter() - started
        return SolveResult(SolveStatus.CANCELLED, statistics=statistics,
                           message="The search was cancelled by the user.")
    except _LimitReached:
        statistics.elapsed_seconds = time.perf_counter() - started
        return SolveResult(SolveStatus.TIMEOUT, statistics=statistics,
                           message="The configured search limit was reached before a solution was proved.")

    completed = [path for paths in states.values() for path in paths]
    valid_paths = []
    for path in completed:
        harmonies = [node.harmony for node in path.nodes]
        voicings = [node.voicing for node in path.nodes]
        cadence = validate_cadence(problem, harmonies, voicings, profile)
        if cadence.hard_violations:
            _record_rejections(cadence, rejection_counts, rejection_samples)
            continue
        score = path.score + cadence.soft_score
        breakdown = _merge_breakdown(path.breakdown, cadence.score_breakdown,
                                      prefix="Cadence: ")
        valid_paths.append(_Path(path.nodes, score, breakdown))

    valid_paths.sort(key=lambda item: (round(item.score, 8), item.tie_key))
    distinct = []
    seen = set()
    for path in valid_paths:
        identity = tuple(node.signature for node in path.nodes)
        if identity in seen:
            continue
        seen.add(identity)
        harmonies = [node.harmony for node in path.nodes]
        voicings = [node.voicing for node in path.nodes]
        independent = evaluate_solution(problem, harmonies, voicings, profile)
        if independent.hard_violations:
            _record_rejections(independent, rejection_counts, rejection_samples)
            continue
        distinct.append(PartWritingSolution(
            voicings=voicings,
            score=independent.soft_score,
            score_breakdown=independent.score_breakdown,
            evaluation=independent,
            harmony_labels=[harmony.label for harmony in harmonies],
        ))
        if len(distinct) >= options.top_k:
            break

    statistics.elapsed_seconds = time.perf_counter() - started
    if distinct:
        return SolveResult(
            SolveStatus.SOLVED, distinct, statistics=statistics,
            message=f"Found {len(distinct)} valid solution{'s' if len(distinct) != 1 else ''}.")
    diagnostics = no_solution_diagnostics(
        problem, profile, [], rejection_counts, rejection_samples)
    return SolveResult(
        SolveStatus.NO_SOLUTION, diagnostics=diagnostics, statistics=statistics,
        message="No solution satisfies every hard rule and user constraint.")


def validate_returned_solution(problem: PartWritingProblem,
                               solution: PartWritingSolution,
                               profile: RuleProfile | None = None) -> RuleEvaluation:
    """Independent public validation helper used by tests and callers."""
    profile = profile or profile_for(problem.profile_id)
    harmonies = []
    for index, label in enumerate(solution.harmony_labels):
        candidates = harmonies_for_slot(problem, index)
        harmony = next((item for item in candidates if item.label == label), None)
        if harmony is None:
            raise ValueError(f"Solution harmony {label!r} is not allowed in slot {index + 1}")
        harmonies.append(harmony)
    return evaluate_solution(problem, harmonies, solution.voicings, profile)


def auto_correct(problem: PartWritingProblem, entered: list[Voicing],
                 profile: RuleProfile | None = None) -> tuple[PartWritingSolution | None,
                                                               list[str], SolveResult]:
    """Repair only cells involved in violations and describe every changed note."""
    from .diagnostics import check_solution

    profile = profile or profile_for(problem.profile_id)
    evaluation = check_solution(problem, entered, profile)
    if not evaluation.hard_violations:
        solution = PartWritingSolution(
            entered, evaluation.soft_score, evaluation.score_breakdown,
            evaluation,
            [slot.harmony.roman_numeral or slot.harmony.chord_symbol or ""
             for slot in problem.slots],
        )
        result = SolveResult(SolveStatus.SOLVED, [solution], message="The entry is already valid.")
        return solution, [], result
    involved = {
        (slot, voice)
        for violation in evaluation.hard_violations
        for slot in violation.slots
        for voice in (violation.voices or VOICE_ORDER)
        if 0 <= slot < len(problem.slots)
    }
    repair = copy.deepcopy(problem)
    for slot_index, (slot, voicing) in enumerate(zip(repair.slots, entered)):
        for voice in VOICE_ORDER:
            constraint = slot.voice(voice)
            if (slot_index, voice) in involved:
                constraint.pitch.exact = None
                constraint.locked = False
            else:
                constraint.pitch.exact = voicing[voice]
                constraint.locked = True
    result = solve(repair, profile, SolverOptions(top_k=20, max_nodes=500_000,
                                                  time_limit_seconds=20.0))
    if not result.solutions:
        return None, [], result
    ranked = sorted(result.solutions, key=lambda solution: (
        sum(solution.voicings[index][voice] != entered[index][voice]
            for index in range(len(entered)) for voice in VOICE_ORDER),
        sum(abs(solution.voicings[index][voice].midi - entered[index][voice].midi)
            for index in range(len(entered)) for voice in VOICE_ORDER),
        solution.score,
        tuple(voicing.spelled_tuple for voicing in solution.voicings),
    ))
    chosen = ranked[0]
    changes = []
    for index, (before, after) in enumerate(zip(entered, chosen.voicings)):
        for voice in VOICE_ORDER:
            if before[voice] != after[voice]:
                changes.append(
                    f"Slot {index + 1} {voice.value}: {before[voice].name} → {after[voice].name}")
    return chosen, changes, result
