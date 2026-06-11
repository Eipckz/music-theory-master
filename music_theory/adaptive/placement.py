"""Adaptive placement test.

A transformed up/down staircase per domain: difficulty rises on correct
answers and falls on errors, with the step shrinking at each reversal so the
estimate converges. It naturally *stops and reports an approximate level* once
the estimate stabilizes or the learner keeps failing above their level - the
language-proficiency behavior requested."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from ..exercises.registry import safe_generate
from .mastery import difficulty_for_rating, level_for_rating, rating_for_difficulty

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
    ],
    "piano": ["play_note", "play_interval", "play_triad", "play_scale"],
}


@dataclass
class _DomainState:
    theta: float = 3.0
    step: float = 2.0
    items: int = 0
    last_correct: Optional[bool] = None
    reversals: int = 0
    thetas: list = field(default_factory=list)
    done: bool = False
    level: str = ""


class PlacementTest:
    def __init__(self, domains=None, *, max_items: int = 9, min_items: int = 5,
                 rng: Optional[random.Random] = None) -> None:
        self.domains = domains or ["theory", "aural", "piano"]
        self.max_items = max_items
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
        return done, self.max_items * len(self.domains)

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
        domain, _etype, _diff, _ex = self._current
        st = self.state[domain]
        st.items += 1
        if st.last_correct is not None and st.last_correct != correct:
            st.reversals += 1
            st.step = max(0.5, st.step * 0.6)
        st.last_correct = correct
        st.theta = max(0.0, min(10.0, st.theta + (st.step if correct else -st.step)))
        st.thetas.append(st.theta)
        self._current = None
        if self._should_stop(st):
            self._finalize(domain, st)

    def _should_stop(self, st: _DomainState) -> bool:
        if st.items >= self.max_items:
            return True
        if st.items >= self.min_items and st.step <= 0.6:
            return True
        # early stop: floored out (consistently failing the easiest items)
        if st.items >= self.min_items and st.theta <= 0.2 and st.last_correct is False:
            return True
        return False

    def _finalize(self, domain: str, st: _DomainState) -> None:
        tail = st.thetas[-3:] if len(st.thetas) >= 3 else st.thetas
        est = sum(tail) / len(tail) if tail else st.theta
        st.theta = est
        st.level = level_for_rating(rating_for_difficulty(est))
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
