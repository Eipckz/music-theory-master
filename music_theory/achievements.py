"""Achievement definitions and evaluation.

Achievements persist in the ``achievements`` table (see storage.db). Evaluation
is idempotent: :meth:`Database.unlock_achievement` only reports an achievement
the first time it is earned, so callers can safely re-check after every action.

Every achievement is computable from existing tables (attempts, profile,
mastery, placement_results, kv); nothing here adds new storage. The gallery
screen shows ALL definitions with locked/unlocked state, so each entry has a
short description of how to earn it.
"""

from __future__ import annotations

from typing import List, Tuple

# key -> (title, how-to-earn description)
ACHIEVEMENTS: dict[str, tuple[str, str]] = {
    # firsts and lesson quality
    "first_lesson": ("First Lesson Complete", "Finish your first 10-exercise lesson."),
    "sharp_shooter": ("Sharp Shooter", "Score 90% or better on a full lesson."),
    "flawless": ("Flawless", "Finish a full lesson with every answer correct."),
    "placement_done": ("Know Thyself", "Complete the placement test."),
    # XP milestones
    "xp_100": ("Century", "Earn 100 total XP."),
    "xp_1000": ("Virtuoso", "Earn 1,000 total XP."),
    "xp_5000": ("Maestro", "Earn 5,000 total XP."),
    "century_day": ("Big Day", "Earn 100 XP in a single day."),
    # streaks
    "streak_3": ("Warming Up", "Practice 3 days in a row."),
    "streak_7": ("On Fire", "Practice 7 days in a row."),
    "streak_14": ("Two-Week Habit", "Practice 14 days in a row."),
    "streak_30": ("Iron Routine", "Practice 30 days in a row."),
    "comeback_streak": ("Comeback", "Rebuild a 3-day streak after losing one."),
    # volume
    "answered_50": ("Getting Serious", "Answer 50 exercises."),
    "answered_250": ("Dedicated", "Answer 250 exercises."),
    "answered_1000": ("Thousand Club", "Answer 1,000 exercises."),
    # mastery
    "first_mastery": ("First Mastery", "Master your first skill."),
    "five_mastery": ("Skill Builder", "Master 5 skills."),
    "twenty_mastery": ("Theorist", "Master 20 skills."),
    "half_curriculum": ("Halfway There", "Master half of the curriculum."),
    "full_curriculum": ("Completionist", "Master every skill in the curriculum."),
    # domain prowess
    "perfect_ear_10": ("Perfect Ear", "Get 10 aural exercises right in a row."),
    "perfect_theory_10": ("Clean Analysis", "Get 10 theory exercises right in a row."),
    "perfect_piano_10": ("Steady Hands", "Get 10 piano exercises right in a row."),
    "dictation_25": ("Take It Down", "Answer 25 melodic dictations correctly."),
    "quick_thinker_25": ("Quick Thinker", "Answer 25 exercises correctly in under 3 seconds each."),
    # habits
    "early_bird": ("Early Bird", "Practice before 8 in the morning."),
    "night_owl": ("Night Owl", "Practice after 11 at night."),
}

# Backwards-compatible title map (used by toasts and the dashboard list).
TITLES: dict[str, str] = {k: v[0] for k, v in ACHIEVEMENTS.items()}


def _mastered_count(db) -> tuple[int, int]:
    from .curriculum import CURRICULUM
    total = sum(1 for s in CURRICULUM if s.schedulable)
    done = sum(1 for s in CURRICULUM if s.schedulable and CURRICULUM.is_mastered(db, s.id))
    return done, total


def _apply(db, checks: List[Tuple[str, bool]]) -> List[str]:
    unlocked: List[str] = []
    for key, condition in checks:
        if condition and db.unlock_achievement(key):
            unlocked.append(TITLES.get(key, key))
    return unlocked


def _domain_run(db, domain: str, n: int = 10) -> bool:
    """True when the most recent n attempts in the domain are all correct."""
    rows = db.conn.execute(
        "SELECT correct FROM attempts WHERE domain = ? ORDER BY ts DESC LIMIT ?",
        (domain, int(n)),
    ).fetchall()
    return len(rows) >= n and all(int(r["correct"]) for r in rows)


def _count_where(db, sql: str, args: tuple = ()) -> int:
    return int(db.conn.execute(sql, args).fetchone()[0])


def _practiced_in_hours(db, lo: int, hi: int) -> bool:
    """Any attempt whose local-time hour is in [lo, hi)."""
    row = db.conn.execute(
        "SELECT 1 FROM attempts WHERE CAST(strftime('%H', ts, 'unixepoch', "
        "'localtime') AS INTEGER) >= ? AND CAST(strftime('%H', ts, 'unixepoch', "
        "'localtime') AS INTEGER) < ? LIMIT 1", (lo, hi),
    ).fetchone()
    return row is not None


def evaluate_global(db) -> List[str]:
    """Check progress-based achievements; return titles newly unlocked."""
    prof = db.get_profile()
    xp = int(prof.get("total_xp", 0))
    streak = int(prof.get("streak_days", 0))
    answered, _correct = db.attempt_counts()
    mastered, total_skills = _mastered_count(db)
    dictations = _count_where(
        db, "SELECT COUNT(*) FROM attempts WHERE exercise_type = 'melodic_dictation' "
            "AND correct = 1")
    quick = _count_where(
        db, "SELECT COUNT(*) FROM attempts WHERE correct = 1 AND response_ms > 0 "
            "AND response_ms < 3000")
    placed = db.conn.execute("SELECT 1 FROM placement_results LIMIT 1").fetchone()
    return _apply(db, [
        ("xp_100", xp >= 100),
        ("xp_1000", xp >= 1000),
        ("xp_5000", xp >= 5000),
        ("century_day", db.today_xp() >= 100),
        ("streak_3", streak >= 3),
        ("streak_7", streak >= 7),
        ("streak_14", streak >= 14),
        ("streak_30", streak >= 30),
        ("comeback_streak", streak >= 3 and bool(db.kv_get("streak.lost_after_3"))),
        ("answered_50", answered >= 50),
        ("answered_250", answered >= 250),
        ("answered_1000", answered >= 1000),
        ("first_mastery", mastered >= 1),
        ("five_mastery", mastered >= 5),
        ("twenty_mastery", mastered >= 20),
        ("half_curriculum", total_skills > 0 and mastered >= total_skills / 2),
        ("full_curriculum", total_skills > 0 and mastered >= total_skills),
        ("perfect_ear_10", _domain_run(db, "aural")),
        ("perfect_theory_10", _domain_run(db, "theory")),
        ("perfect_piano_10", _domain_run(db, "piano")),
        ("dictation_25", dictations >= 25),
        ("quick_thinker_25", quick >= 25),
        ("early_bird", _practiced_in_hours(db, 5, 8)),
        ("night_owl", _practiced_in_hours(db, 23, 24) or _practiced_in_hours(db, 0, 5)),
        ("placement_done", placed is not None),
    ])


def evaluate_lesson(db, *, accuracy: int, lesson_len: int) -> List[str]:
    """Check lesson-completion achievements plus all global ones."""
    lesson = _apply(db, [
        ("first_lesson", lesson_len >= 1),
        ("sharp_shooter", accuracy >= 90 and lesson_len >= 5),
        ("flawless", accuracy >= 100 and lesson_len >= 5),
    ])
    return lesson + evaluate_global(db)


def unlocked_titles(db) -> List[str]:
    """Titles of all achievements the learner has earned, in unlock order."""
    return [TITLES.get(k, k) for k in db.achievements()]
