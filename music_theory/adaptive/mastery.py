"""Per-skill mastery estimation and spaced-repetition scheduling.

Combines three signals per skill:
* an Elo-style ability ``rating`` (vs item difficulty),
* a Bayesian Knowledge Tracing probability ``mastery_prob`` (P known),
* an FSRS-lite memory ``stability`` driving the next review ``due_at``.

The same model is updated from coursework, practice, and placement, so getting
better anywhere immediately raises difficulty everywhere (cross-feature
feedback) and weak skills resurface sooner."""

from __future__ import annotations

import time
from dataclasses import dataclass

DAY = 86400.0

LEVELS = [
    (0, "Beginner"),
    (900, "Early"),
    (1150, "Intermediate"),
    (1400, "Advanced"),
    (1650, "Graduate"),
]

# Elo
_K = 28.0
_BASE_RATING = 700.0
_RATING_PER_DIFF = 130.0

# BKT
_GUESS = 0.20
_SLIP = 0.10
_TRANSIT = 0.14

# FSRS-lite
_MIN_STABILITY = 0.30   # days until first review after a lapse
_INITIAL_STABILITY = 1.0


def rating_for_difficulty(difficulty: float) -> float:
    return _BASE_RATING + difficulty * _RATING_PER_DIFF


def difficulty_for_rating(rating: float) -> float:
    return max(0.0, min(10.0, (rating - _BASE_RATING) / _RATING_PER_DIFF))


def level_for_rating(rating: float) -> str:
    label = LEVELS[0][1]
    for threshold, name in LEVELS:
        if rating >= threshold:
            label = name
    return label


def _expected(rating: float, item_rating: float) -> float:
    return 1.0 / (1.0 + 10.0 ** ((item_rating - rating) / 400.0))


@dataclass
class MasteryUpdate:
    rating: float
    mastery_prob: float
    stability: float
    due_at: float


class MasteryModel:
    """Stateless calculator; persistence happens through the Database."""

    def update_on_attempt(
        self, db, skill_id: str, correct: bool, *, difficulty: float,
        domain: str = "", etype: str = "", response_ms: int = 0,
        source: str = "course", now: float | None = None,
    ) -> MasteryUpdate:
        now = time.time() if now is None else now
        cur = db.get_mastery(skill_id) or {}
        rating = float(cur.get("rating", 1000.0))
        pL = float(cur.get("mastery_prob", 0.10))
        stability = float(cur.get("stability", 0.0))
        reps = int(cur.get("reps", 0))
        lapses = int(cur.get("lapses", 0))
        n_att = int(cur.get("n_attempts", 0))
        n_cor = int(cur.get("n_correct", 0))

        item_rating = rating_for_difficulty(difficulty)
        exp = _expected(rating, item_rating)
        rating = rating + _K * ((1.0 if correct else 0.0) - exp)

        pL = self._bkt(pL, correct)

        if correct:
            growth = 1.4 + 1.2 * pL          # stronger memory when more mastered
            stability = max(_INITIAL_STABILITY, stability * growth if stability else _INITIAL_STABILITY)
            reps += 1
        else:
            stability = _MIN_STABILITY
            lapses += 1
        due_at = now + stability * DAY

        n_att += 1
        n_cor += 1 if correct else 0

        db.upsert_mastery(
            skill_id, rating=rating, mastery_prob=pL, stability=stability,
            difficulty=difficulty, reps=reps, lapses=lapses, n_attempts=n_att,
            n_correct=n_cor, last_seen=now, due_at=due_at,
            unlocked=int(cur.get("unlocked", 1)) or 1,
        )
        db.log_attempt(
            skill_id, correct, domain=domain, exercise_type=etype,
            difficulty=difficulty, response_ms=response_ms, source=source,
        )
        return MasteryUpdate(rating, pL, stability, due_at)

    @staticmethod
    def _bkt(pL: float, correct: bool) -> float:
        if correct:
            num = pL * (1 - _SLIP)
            den = pL * (1 - _SLIP) + (1 - pL) * _GUESS
        else:
            num = pL * _SLIP
            den = pL * _SLIP + (1 - pL) * (1 - _GUESS)
        post = num / den if den > 0 else pL
        return post + (1 - post) * _TRANSIT

    @staticmethod
    def overall_rating(db, skill_ids=None) -> float:
        m = db.all_mastery()
        if skill_ids is not None:
            m = {k: v for k, v in m.items() if k in skill_ids}
        seen = [v for v in m.values() if v.get("n_attempts", 0) > 0]
        if not seen:
            # No evidence yet: report the true floor, not a flattering default.
            return _BASE_RATING
        return sum(v["rating"] for v in seen) / len(seen)
