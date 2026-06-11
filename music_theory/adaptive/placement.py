"""Adaptive placement test.

A transformed 2-up/1-down staircase per domain: difficulty rises only after
*two consecutive* correct answers and falls on every error, so the estimate
converges on the ~71%-correct point - a level the learner is genuinely secure
at, not one they can reach by lucky multiple-choice guessing. The staircase is
followed by a short confirmation phase at the estimated level, and the final
estimate is capped at the hardest item actually answered correctly, so the
test reports the learner's TRUE working level rather than an optimistic one.
It still stops early when the learner keeps failing the easiest items."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from ..exercises.registry import safe_generate
from .mastery import level_for_rating, rating_for_difficulty

# Representative exercise types per domain, ordered easy -> hard.
_DOMAIN_LADDER = {
    "theory": [
        "note_identification", "interval_identification", "key_signature_identification",
        "triad_quality", "seventh_quality", "chord_inversion", "roman_numeral_analysis",
        "pcset_prime_form", "row_form_identification",
    ],
    "aural": [
        "interval_recognition", "chord_quality_ear", "scale_mode_ear",
        "melodic_dictation", "cadence_ear", "harmonic_dictation",
        "multipart_dictation",
    ],
    "piano": ["play_note", "play_interval", "play_triad", "play_scale"],
}

_CONFIRM_ITEMS = 2      # items presented at the estimated level after converging
_CONFIRM_PENALTY = 0.8  # estimate drop for each failed confirmation item


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


class PlacementTest:
    def __init__(self, domains=None, *, max_items: int = 10, min_items: int = 6,
                 rng: Optional[random.Random] = None) -> None:
        self.domains = domains or ["theory", "aural", "piano"]
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
        return done, (self.max_items + _CONFIRM_ITEMS) * len(self.domains)

    def next_item(self):
        domain = self.current_domain
        if domain is None:
            return None
        st = self.state[domain]
        etype = self._pick_etype(domain, st.theta)
        ex = safe_generate(etype, st.theta, self.rng)
        self._current = (domain, etype, st.theta, ex)
        return ex

    def submit(self, correct: bool) -> None:
        if self._current is None:
            return
        domain, _etype, diff, _ex = self._current
        st = self.state[domain]
        st.items += 1
        st.history.append((diff, bool(correct)))
        self._current = None
        if st.phase == "confirm":
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
            self._finalize(domain, st)
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
                "level": s.level or level_for_rating(rating_for_difficulty(s.theta))}
            for d, s in self.state.items()
        }

    def save(self, db, apply_result: Optional[Callable[[str, float], None]] = None) -> dict:
        res = self.results()
        for domain, info in res.items():
            st = self.state[domain]
            db.save_placement(domain, info["theta"],
                              ci=max(0.5, st.step), level=info["level"], n_items=st.items)
            db.kv_set(f"placement.theta.{domain}", info["theta"])
            if apply_result is not None:
                apply_result(domain, info["theta"])
        db.kv_set("placement.completed_at", time.time())
        return res
