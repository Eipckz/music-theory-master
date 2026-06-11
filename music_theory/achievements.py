"""Achievement definitions and evaluation.

Achievements persist in the ``achievements`` table (see storage.db). Evaluation
is idempotent: :meth:`Database.unlock_achievement` only reports an achievement
the first time it is earned, so callers can safely re-check after every action."""

from __future__ import annotations

from typing import List, Tuple

# key -> human title (used for unlock toasts and the dashboard list)
TITLES: dict[str, str] = {
    "first_lesson": "First Lesson Complete",
    "sharp_shooter": "Sharp Shooter - 90%+ lesson",
    "xp_100": "Century - 100 XP",
    "xp_1000": "Virtuoso - 1000 XP",
    "streak_3": "Warming Up - 3-day streak",
    "streak_7": "On Fire - 7-day streak",
    "answered_50": "Getting Serious - 50 exercises",
    "answered_250": "Dedicated - 250 exercises",
    "first_mastery": "First Mastery",
    "five_mastery": "Skill Builder - 5 skills mastered",
    "twenty_mastery": "Theorist - 20 skills mastered",
}


def _mastered_count(db) -> int:
    from .curriculum import CURRICULUM
    return sum(1 for s in CURRICULUM if s.schedulable and CURRICULUM.is_mastered(db, s.id))


def _apply(db, checks: List[Tuple[str, bool]]) -> List[str]:
    unlocked: List[str] = []
    for key, condition in checks:
        if condition and db.unlock_achievement(key):
            unlocked.append(TITLES.get(key, key))
    return unlocked


def evaluate_global(db) -> List[str]:
    """Check progress-based achievements; return titles newly unlocked."""
    prof = db.get_profile()
    xp = int(prof.get("total_xp", 0))
    streak = int(prof.get("streak_days", 0))
    answered, _correct = db.attempt_counts()
    mastered = _mastered_count(db)
    return _apply(db, [
        ("xp_100", xp >= 100),
        ("xp_1000", xp >= 1000),
        ("streak_3", streak >= 3),
        ("streak_7", streak >= 7),
        ("answered_50", answered >= 50),
        ("answered_250", answered >= 250),
        ("first_mastery", mastered >= 1),
        ("five_mastery", mastered >= 5),
        ("twenty_mastery", mastered >= 20),
    ])


def evaluate_lesson(db, *, accuracy: int, lesson_len: int) -> List[str]:
    """Check lesson-completion achievements plus all global ones."""
    lesson = _apply(db, [
        ("first_lesson", lesson_len >= 1),
        ("sharp_shooter", accuracy >= 90 and lesson_len >= 5),
    ])
    return lesson + evaluate_global(db)


def unlocked_titles(db) -> List[str]:
    """Titles of all achievements the learner has earned, in unlock order."""
    return [TITLES.get(k, k) for k in db.achievements()]
