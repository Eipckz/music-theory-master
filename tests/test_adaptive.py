"""Adaptive engine: mastery updates, placement convergence, scheduling."""

from __future__ import annotations

import math
import random

from music_theory.adaptive import (
    MasteryModel, PlacementTest, Scheduler, difficulty_for_rating, level_for_rating,
)
from music_theory.curriculum import CURRICULUM


def _answer(diff, ability, rng):
    return rng.random() < 1.0 / (1.0 + math.exp((diff - ability) * 0.7))


def test_rating_moves_with_outcome(db):
    m = MasteryModel()
    up_c = m.update_on_attempt(db, "s.correct", True, difficulty=5.0)
    up_w = m.update_on_attempt(db, "s.wrong", False, difficulty=5.0)
    assert up_c.rating > 1000.0
    assert up_w.rating < 1000.0


def test_mastery_prob_rises_with_practice(db):
    m = MasteryModel()
    prob = 0.0
    for _ in range(8):
        prob = m.update_on_attempt(db, "s.learn", True, difficulty=3.0).mastery_prob
    assert prob > 0.8


def test_due_scheduling_increases_interval(db):
    m = MasteryModel()
    first = m.update_on_attempt(db, "s.due", True, difficulty=3.0)
    second = m.update_on_attempt(db, "s.due", True, difficulty=3.0)
    assert second.stability > first.stability


def _run_placement(true_theta, trial, guess=0.0):
    rng = random.Random(trial)
    pt = PlacementTest(domains=["theory"], rng=rng)
    while not pt.finished:
        pt.next_item()
        d = pt.state["theory"].theta
        p = 1.0 / (1.0 + math.exp((d - true_theta) * 0.7))
        pt.submit(rng.random() < guess + (1 - guess) * p)
    return pt.results()["theory"]["theta"]


def test_placement_converges():
    """The 2-up/1-down design deliberately anchors on the ~71%-correct point
    (a level the learner is *secure* at), so estimates sit at or slightly
    below true ability - never far above it."""
    for true_theta in (1.5, 8.0):
        ests = [_run_placement(true_theta, trial) for trial in range(15)]
        mean = sum(ests) / len(ests)
        if true_theta < 5:
            assert mean < 3.0
        else:
            assert mean > 5.0


def test_placement_resists_overestimation():
    """Even with a 25% multiple-choice guessing floor, a true beginner must
    not be placed above the Beginner/Early boundary on average, and lucky
    streaks must stay rare."""
    ests = [_run_placement(0.5, trial, guess=0.25) for trial in range(40)]
    mean = sum(ests) / len(ests)
    assert mean < 1.5
    assert sum(1 for e in ests if e > 2.5) / len(ests) < 0.1


def test_placement_caps_at_demonstrated_difficulty():
    """A learner who never answers anything correctly places at the floor."""
    rng = random.Random(7)
    pt = PlacementTest(domains=["theory"], rng=rng)
    while not pt.finished:
        pt.next_item()
        pt.submit(False)
    assert pt.results()["theory"]["theta"] <= 0.5


def test_scheduler_bootstrap_and_pick(db):
    sched = Scheduler(db, CURRICULUM, rng=random.Random(0))
    sched.ensure_bootstrap()
    assert CURRICULUM.unlocked_skills(db)
    pick = sched.next_exercise()
    assert pick is not None
    assert pick.exercise.grade(pick.exercise.answer)


def test_scheduler_unlocks_with_mastery(db):
    sched = Scheduler(db, CURRICULUM, rng=random.Random(2))
    sched.ensure_bootstrap()
    before = len(CURRICULUM.unlocked_skills(db))
    for _ in range(300):
        pick = sched.next_exercise()
        skill = CURRICULUM.get(pick.skill_id)
        sched.record(pick.skill_id, True, difficulty=pick.difficulty,
                     domain=skill.domain, etype=pick.etype)
    after = len(CURRICULUM.unlocked_skills(db))
    assert after > before
