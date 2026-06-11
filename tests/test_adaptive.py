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


def test_placement_converges():
    for true_theta in (1.5, 8.0):
        ests = []
        for trial in range(15):
            rng = random.Random(trial)
            pt = PlacementTest(domains=["theory"], rng=rng)
            while not pt.finished:
                ex = pt.next_item()
                d = pt.state["theory"].theta
                pt.submit(_answer(d, true_theta, rng))
            ests.append(pt.results()["theory"]["theta"])
        mean = sum(ests) / len(ests)
        if true_theta < 5:
            assert mean < 4.0
        else:
            assert mean > 6.0


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
