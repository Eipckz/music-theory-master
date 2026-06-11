"""Progress persistence: daily XP, achievements, progress reset, non-destructive
placement re-seeding, and weak-skill scheduling."""

from __future__ import annotations

import random

from music_theory.achievements import evaluate_global, evaluate_lesson, unlocked_titles
from music_theory.adaptive import Scheduler
from music_theory.curriculum import CURRICULUM


def test_daily_xp_tracks_and_resets(db):
    assert db.today_xp() == 0
    db.add_xp(15)
    db.add_xp(10)
    assert db.today_xp() == 25
    db.reset_progress()
    assert db.today_xp() == 0
    assert db.get_profile()["total_xp"] == 0


def test_reset_progress_clears_everything(db):
    db.upsert_mastery("fund.note_names", rating=1400, mastery_prob=0.9, n_attempts=5, unlocked=1)
    db.log_attempt("fund.note_names", True, domain="theory")
    db.save_placement("theory", 5.0, ci=1.0, level="Intermediate", n_items=8)
    db.unlock_achievement("first_lesson")
    db.add_xp(50)

    db.reset_progress()

    assert db.all_mastery() == {}
    assert db.attempt_counts() == (0, 0)
    assert db.latest_placement() == {}
    assert db.achievements() == []
    assert db.get_profile()["total_xp"] == 0


def test_achievements_unlock_once(db):
    db.add_xp(120)
    first = evaluate_global(db)
    assert "Century" in first
    # idempotent: re-evaluating does not re-award
    assert evaluate_global(db) == []
    assert "Century" in unlocked_titles(db)


def test_lesson_achievement_sharp_shooter(db):
    titles = evaluate_lesson(db, accuracy=95, lesson_len=10)
    assert "First Lesson Complete" in titles
    assert "Sharp Shooter" in titles


def test_placement_reseed_does_not_downgrade(db):
    # Learner already strong in theory.
    for s in CURRICULUM.by_domain("theory"):
        if s.schedulable:
            db.upsert_mastery(s.id, rating=1500.0, mastery_prob=0.95, unlocked=1, n_attempts=8)
    CURRICULUM.seed_from_placement(db, "theory", 2.0)  # a low retake result
    for s in CURRICULUM.by_domain("theory"):
        if s.schedulable:
            m = db.get_mastery(s.id)
            assert m["rating"] >= 1500.0
            assert m["mastery_prob"] >= 0.95


def test_scheduler_weak_mode_targets_low_mastery(db):
    sched = Scheduler(db, CURRICULUM, rng=random.Random(3))
    sched.ensure_bootstrap()
    unlocked = CURRICULUM.unlocked_skills(db)
    assert len(unlocked) >= 2
    # Give every unlocked skill solid (but not mastered, to avoid cascade
    # unlocks) mastery, then make one clearly the weakest.
    for s in unlocked:
        db.upsert_mastery(s.id, mastery_prob=0.9, n_attempts=2, unlocked=1)
    weak = unlocked[0]
    db.upsert_mastery(weak.id, mastery_prob=0.01, n_attempts=2, unlocked=1)
    picks = {sched.next_exercise(weak=True).skill_id for _ in range(20)}
    assert picks == {weak.id}
