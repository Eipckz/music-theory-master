"""Next-item selection for coursework.

Balances three needs: spaced-repetition reviews that are due, skills in the
learner's zone of proximal development (still being learned), and introducing
newly-unlocked skills. Difficulty for each item is drawn from the skill's
current Elo rating clamped to the skill's band, so practice gains immediately
raise coursework difficulty."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Optional

from ..exercises.registry import safe_generate
from .mastery import MasteryModel, difficulty_for_rating


@dataclass
class Pick:
    skill_id: str
    etype: str
    difficulty: float
    exercise: object
    reason: str


class Scheduler:
    def __init__(self, db, curriculum, *, rng: Optional[random.Random] = None) -> None:
        self.db = db
        self.curriculum = curriculum
        self.rng = rng or random.Random()
        self.mastery = MasteryModel()

    def ensure_bootstrap(self) -> None:
        """Unlock the root (no-prerequisite) skills for a fresh learner."""
        if self.curriculum.unlocked_skills(self.db):
            return
        for s in self.curriculum:
            if s.schedulable and not s.prereqs:
                self.db.upsert_mastery(s.id, unlocked=1)

    def _difficulty_for(self, skill) -> float:
        m = self.db.get_mastery(skill.id)
        lo, hi = skill.diff_range
        if not m or m.get("n_attempts", 0) == 0:
            base = lo + 0.5
        else:
            base = difficulty_for_rating(m["rating"])
        jitter = self.rng.uniform(-0.4, 0.6)
        return max(lo, min(hi, base + jitter))

    def next_exercise(self, *, source: str = "course", weak: bool = False) -> Optional[Pick]:
        self.ensure_bootstrap()
        now = time.time()
        unlocked = self.curriculum.unlocked_skills(self.db)
        if not unlocked:
            return None

        if weak:
            ranked = sorted(
                unlocked,
                key=lambda s: (self.db.get_mastery(s.id) or {}).get("mastery_prob", 0.0),
            )
            pool = ranked[: max(1, len(ranked) // 3)]
            chosen = self.rng.choice(pool)
            difficulty = self._difficulty_for(chosen)
            etype = self.rng.choice(chosen.etypes)
            return Pick(chosen.id, etype, difficulty,
                        safe_generate(etype, difficulty, self.rng), "weak spot")

        due = []
        for s in unlocked:
            m = self.db.get_mastery(s.id)
            if m and m.get("n_attempts", 0) > 0 and m.get("due_at", 0) <= now \
                    and m.get("mastery_prob", 0) < 0.98:
                due.append((m["due_at"], s))
        reason = "review"
        chosen = None

        if due and self.rng.random() < 0.5:
            due.sort(key=lambda t: t[0])
            chosen = due[0][1]
        else:
            new = self.curriculum.newly_available(self.db)
            if new and self.rng.random() < 0.28:
                chosen = self.rng.choice(new)
                self.db.upsert_mastery(chosen.id, unlocked=1)
                reason = "new skill"
            else:
                learning = [s for s in unlocked
                            if (self.db.get_mastery(s.id) or {}).get("mastery_prob", 0.1) < 0.95]
                pool = learning or unlocked
                weights = [1.05 - (self.db.get_mastery(s.id) or {}).get("mastery_prob", 0.1)
                           for s in pool]
                chosen = self.rng.choices(pool, weights=weights, k=1)[0]
                reason = "practice"

        difficulty = self._difficulty_for(chosen)
        etype = self.rng.choice(chosen.etypes)
        ex = safe_generate(etype, difficulty, self.rng)
        return Pick(chosen.id, etype, difficulty, ex, reason)

    def record(self, skill_id: str, correct: bool, *, difficulty: float, domain: str,
               etype: str, response_ms: int = 0, source: str = "course") -> None:
        self.mastery.update_on_attempt(
            self.db, skill_id, correct, difficulty=difficulty, domain=domain,
            etype=etype, response_ms=response_ms, source=source,
        )
        # newly satisfied prerequisites unlock their dependents
        for s in self.curriculum.newly_available(self.db):
            pass  # availability is computed on demand; nothing to persist here

    # -- stats helpers ----------------------------------------------------
    def progress_summary(self) -> dict:
        total = sum(1 for s in self.curriculum if s.schedulable)
        unlocked = len(self.curriculum.unlocked_skills(self.db))
        mastered = sum(1 for s in self.curriculum
                       if s.schedulable and self.curriculum.is_mastered(self.db, s.id))
        return {"total": total, "unlocked": unlocked, "mastered": mastered}
