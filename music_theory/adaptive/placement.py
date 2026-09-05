"""Adaptive placement test.

A transformed 2-up/1-down staircase per domain: difficulty rises only after
*two consecutive* correct answers and falls on every error, so the estimate
converges on the ~71%-correct point - a level the learner is genuinely secure
at, not one they can reach by lucky multiple-choice guessing. The staircase is
followed by a short confirmation phase at the estimated level, and the final
estimate is capped at the hardest item actually answered correctly, so the
test produces a conservative practice starting point. It is not a validated
measurement of complete musicianship. Optional breadth checks record topic
evidence and can lower the estimate when knowledge is uneven."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from ..exercises.registry import generate, title_of
from .mastery import level_for_rating, rating_for_difficulty

# Representative exercise types per domain, ordered easy -> hard.
_DOMAIN_LADDER = {
    "theory": [
        "note_identification", "interval_identification", "key_signature_identification",
        "triad_quality", "seventh_quality", "chord_inversion", "roman_numeral_analysis",
        "modal_degree", "dominant_tendency", "chromatic_function", "modulation_evidence",
        "pitch_class_conversion", "interval_class_identification", "pcset_prime_form",
        "row_form_identification",
    ],
    "aural": [
        "interval_recognition", "chord_quality_ear", "scale_mode_ear",
        "melodic_dictation", "cadence_ear", "harmonic_dictation",
        "multipart_dictation", "posttonal_interval_ear", "pcset_cardinality_ear",
    ],
    "piano": ["play_note", "play_interval", "play_triad", "play_scale",
              "play_pitch_class_set", "play_row_segment", "play_plr_transform"],
}

_CONFIRM_ITEMS = 2      # items presented at the estimated level after converging
_CONFIRM_PENALTY = 0.8  # estimate drop for each failed confirmation item

# Deliberate breadth checks, in addition to adaptive difficulty sampling.
_COVERAGE = {
    "theory": [("key_signature_identification", 0), ("interval_construction", 0),
               ("triad_spelling", 0), ("modal_degree", 4), ("dominant_tendency", 4),
               ("nonchord_tone", 4), ("chromatic_function", 6), ("modulation_evidence", 6)],
    "aural": [("rhythmic_dictation", 0), ("interval_recognition", 0),
              ("melodic_dictation", 2), ("cadence_ear", 3)],
    "piano": [("play_note", 0), ("play_interval", 0), ("play_triad", 2), ("play_scale", 3)],
}


@dataclass
class _DomainState:
    theta: float = 2.0
    step: float = 2.0
    items: int = 0
    last_correct: Optional[bool] = None
    last_move: int = 0              # -1 down, +1 up, 0 none yet
    streak: int = 0                 # consecutive correct (2 needed to move up)
    ramp: bool = True               # fast 1-up climb until the first miss
    reversals: int = 0
    thetas: list = field(default_factory=list)
    history: list = field(default_factory=list)   # (difficulty, correct)
    phase: str = "staircase"        # staircase -> confirm -> done
    confirm_left: int = _CONFIRM_ITEMS
    done: bool = False
    level: str = ""
    evidence: list = field(default_factory=list)
    coverage_queue: list = field(default_factory=list)


class PlacementTest:
    def __init__(self, domains=None, *, max_items: int = 10, min_items: int = 6,
                 rng: Optional[random.Random] = None, comprehensive: bool = False) -> None:
        self.domains = domains or ["theory", "aural", "piano"]
        if any(d not in _DOMAIN_LADDER for d in self.domains) or len(set(self.domains)) != len(self.domains):
            raise ValueError("Choose distinct theory, aural and/or piano domains.")
        if not 1 <= min_items <= max_items <= 50:
            raise ValueError("Placement item bounds must satisfy 1 <= minimum <= maximum <= 50.")
        self.comprehensive = comprehensive
        self.max_items = max_items          # staircase items per domain
        self.min_items = min_items
        self.rng = rng or random.Random()
        self.state = {d: _DomainState() for d in self.domains}
        self._di = 0
        self._current = None   # (domain, etype, difficulty, exercise)

    # -- iteration --------------------------------------------------------
    @property
    def current_domain(self) -> Optional[str]:
        while self._di < len(self.domains) and self.state[self.domains[self._di]].done:
            self._di += 1
        return self.domains[self._di] if self._di < len(self.domains) else None

    @property
    def finished(self) -> bool:
        return self.current_domain is None

    @property
    def progress(self) -> tuple[int, int]:
        done = sum(s.items for s in self.state.values())
        extra = sum(len(_COVERAGE[d]) for d in self.domains) if self.comprehensive else 0
        return done, (self.max_items + _CONFIRM_ITEMS) * len(self.domains) + extra

    def next_item(self):
        if self._current is not None:
            return self._current[3]
        domain = self.current_domain
        if domain is None:
            return None
        st = self.state[domain]
        etype = st.coverage_queue[0] if st.phase == "coverage" else self._pick_etype(domain, st.theta)
        # A fallback tonic question must never be credited as an advanced aural item.
        # Retry the requested type and record the actual presented difficulty.
        for retry in range(4):
            diff = max(0., st.theta - .75 * retry)
            try:
                ex = generate(etype, diff, self.rng)
                if ex.etype != etype or ex.domain != domain:
                    raise ValueError("Placement generator returned an unrelated exercise")
                break
            except Exception:
                if retry == 3:
                    raise
        self._current = (domain, etype, diff, ex)
        return ex

    def submit(self, correct: bool) -> None:
        if self._current is None:
            return
        domain, etype, diff, _ex = self._current
        st = self.state[domain]
        st.items += 1
        st.history.append((diff, bool(correct)))
        st.evidence.append({"type": etype, "title": title_of(etype), "difficulty": round(diff, 2),
                            "correct": bool(correct), "phase": st.phase})
        self._current = None
        if st.phase == "coverage":
            st.coverage_queue.pop(0)
            if not st.coverage_queue:
                self._finalize(domain, st)
        elif st.phase == "confirm":
            self._submit_confirm(domain, st, correct)
        else:
            self._submit_staircase(domain, st, correct)

    # -- staircase phase ----------------------------------------------------
    def _submit_staircase(self, domain: str, st: _DomainState, correct: bool) -> None:
        move = 0
        if correct:
            st.streak += 1
            if st.ramp or st.streak >= 2:   # fast ramp early; 2-up once tested
                move = 1
                st.streak = 0
        else:
            move = -1                   # 1-down: every miss eases difficulty
            st.streak = 0
            st.ramp = False             # first miss ends the fast climb
        if move != 0:
            if st.last_move != 0 and move != st.last_move:
                st.reversals += 1
                st.step = max(0.5, st.step * 0.6)
            st.last_move = move
            st.theta = max(0.0, min(10.0, st.theta + move * st.step))
        st.last_correct = correct
        st.thetas.append(st.theta)
        if self._staircase_should_stop(st):
            self._to_confirm(domain, st)

    def _staircase_should_stop(self, st: _DomainState) -> bool:
        if st.items >= self.max_items:
            return True
        if st.items >= self.min_items and st.step <= 0.6 and st.reversals >= 2:
            return True
        # early stop: floored out (consistently failing the easiest items)
        if st.items >= self.min_items and st.theta <= 0.2 and st.last_correct is False:
            return True
        return False

    def _to_confirm(self, domain: str, st: _DomainState) -> None:
        est = self._estimate(st)
        st.theta = est
        if est <= 0.2:
            # Nothing meaningful to confirm at the floor - finish here.
            self._to_coverage(domain, st)
            return
        st.phase = "confirm"
        st.confirm_left = _CONFIRM_ITEMS

    # -- confirmation phase ---------------------------------------------------
    def _submit_confirm(self, domain: str, st: _DomainState, correct: bool) -> None:
        if not correct:
            # The estimated level wasn't secure - place below it.
            st.theta = max(0.0, st.theta - _CONFIRM_PENALTY)
        st.confirm_left -= 1
        if st.confirm_left <= 0:
            self._to_coverage(domain, st)

    def _to_coverage(self, domain, st):
        if self.comprehensive:
            st.coverage_queue = [etype for etype, minimum in _COVERAGE[domain] if st.theta >= minimum]
            if st.coverage_queue:
                st.phase = "coverage"
                return
        self._finalize(domain, st)

    # -- estimation ------------------------------------------------------------
    @staticmethod
    def _estimate(st: _DomainState) -> float:
        """Conservative level estimate from the staircase trajectory."""
        tail = st.thetas[-3:] if len(st.thetas) >= 3 else st.thetas
        est = sum(tail) / len(tail) if tail else st.theta
        # Never place someone above what they have *repeatedly* demonstrated:
        # the cap is the second-hardest item answered correctly, so a single
        # lucky multiple-choice guess cannot inflate the placement.
        correct_diffs = sorted((d for d, ok in st.history if ok), reverse=True)
        if not correct_diffs:
            cap = 0.0
        elif len(correct_diffs) == 1:
            cap = min(correct_diffs[0], 1.0)
        else:
            cap = correct_diffs[1]
        return max(0.0, min(est, cap))

    def _finalize(self, domain: str, st: _DomainState) -> None:
        coverage = [e for e in st.evidence if e["phase"] == "coverage"]
        if coverage:
            misses = sum(not e["correct"] for e in coverage)
            st.theta = max(0., st.theta - min(1.5, misses * .35))
        # Confirmation and coverage can only lower the demonstrated cap.
        correct = sorted((d for d, ok in st.history if ok), reverse=True)
        cap = correct[1] if len(correct) >= 2 else min(correct[0], 1.) if correct else 0.
        st.theta = min(st.theta, cap)
        st.level = level_for_rating(rating_for_difficulty(st.theta))
        st.phase = "done"
        st.done = True

    def _pick_etype(self, domain: str, theta: float) -> str:
        ladder = _DOMAIN_LADDER[domain]
        idx = round((theta / 10.0) * (len(ladder) - 1))
        idx = max(0, min(len(ladder) - 1, idx + self.rng.choice([-1, 0, 0, 1])))
        return ladder[idx]

    # -- results ----------------------------------------------------------
    def results(self) -> dict:
        return {
            d: {"theta": round(s.theta, 2),
                "rating": round(rating_for_difficulty(s.theta)),
                "level": s.level or level_for_rating(rating_for_difficulty(s.theta)),
                "complete": s.done, "items": s.items,
                "topics": len({e["type"] for e in s.evidence}),
                "evidence": list(s.evidence),
                "review": sorted({e["title"] for e in s.evidence if not e["correct"]})}
            for d, s in self.state.items()
        }

    def save(self, db, apply_result: Optional[Callable[[str, float], None]] = None) -> dict:
        if not self.finished:
            raise ValueError("Complete the assessment before saving placement results.")
        res = self.results()
        for domain, info in res.items():
            st = self.state[domain]
            db.save_placement(domain, info["theta"],
                              ci=max(0.5, st.step), level=info["level"], n_items=st.items)
            db.kv_set(f"placement.theta.{domain}", info["theta"])
            db.kv_set(f"placement.evidence.{domain}", info)
            if apply_result is not None:
                apply_result(domain, info["theta"])
        db.kv_set("placement.completed_at", time.time())
        return res
