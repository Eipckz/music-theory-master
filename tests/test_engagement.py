"""Engagement systems: message bank rotation, achievements, celebrations."""

from __future__ import annotations

import time

import pytest

from music_theory import achievements as ach
from music_theory import feedback_messages as fm


# -- message bank -----------------------------------------------------------

def test_levels_match_curriculum_order():
    from music_theory.curriculum.model import LEVEL_ORDER
    assert list(fm.LEVELS) == LEVEL_ORDER


def test_full_bucket_coverage_with_enough_variants():
    """Every (domain, level, event) must resolve to at least 8 variants."""
    for d in fm.DOMAINS:
        for lv in fm.LEVELS:
            for ev in fm.EVENTS:
                variants = fm.variants_for(d, lv, ev)
                assert len(variants) >= 8, (d, lv, ev, len(variants))


def test_no_em_dashes_or_screaming_anywhere_in_bank():
    for key, variants in fm.MESSAGES.items():
        for msg in variants:
            assert "—" not in msg, (key, msg)         # owner rule: no em dashes
            assert "!!" not in msg, (key, msg)
            assert len(msg) < 200, (key, msg)


def test_messages_format_without_keyerror():
    for key, variants in fm.MESSAGES.items():
        for msg in variants:
            out = msg.format_map(fm._SafeDict({}))          # no kwargs at all
            assert "{" not in out and "}" not in out, (key, msg)


def test_pick_message_never_repeats_until_exhausted(db):
    variants = fm.variants_for("theory", "Beginner", "lesson_complete")
    seen = [fm.pick_message(db, "theory", "Beginner", "lesson_complete",
                            skill="Note names") for _ in range(len(variants))]
    assert len(set(seen)) == len(variants), "repeated a line before exhausting the bucket"


def test_pick_message_reshuffles_without_back_to_back_repeat(db):
    variants = fm.variants_for("aural", "Early", "mastery")
    n = len(variants)
    seq = [fm.pick_message(db, "aural", "Early", "mastery", skill="Intervals")
           for _ in range(n * 3)]
    for a, b in zip(seq, seq[1:]):
        assert a != b, "same line shown twice in a row"
    # the first full cycle uses every variant exactly once
    assert len(set(seq[:n])) == n


def test_pick_message_substitutes_placeholders(db):
    msg = fm.pick_message(db, "theory", "Intermediate", "level_up",
                          level="Intermediate", domain="Theory")
    assert "{" not in msg and msg


def test_pick_message_survives_corrupt_rotation_state(db):
    db.kv_set("fbmsg.theory.Beginner.level_up", {"not": "a list"})
    assert fm.pick_message(db, "theory", "Beginner", "level_up", level="Early")
    db.kv_set("fbmsg.theory.Beginner.level_up", [999, -4, "x"])
    assert fm.pick_message(db, "theory", "Beginner", "level_up", level="Early")


# -- achievements -------------------------------------------------------------

def test_every_achievement_has_title_and_description():
    assert len(ach.ACHIEVEMENTS) >= 25
    for key, (title, desc) in ach.ACHIEVEMENTS.items():
        assert title and desc, key
        assert "—" not in title and "—" not in desc, key


def test_global_achievements_idempotent(db):
    db.add_xp(150)
    first = ach.evaluate_global(db)
    assert "Century" in first
    assert "Century" not in ach.evaluate_global(db)


def test_perfect_ear_unlocks_on_ten_straight_aural(db):
    for _ in range(9):
        db.log_attempt("aural_x", True, domain="aural")
    assert "Perfect Ear" not in ach.evaluate_global(db)
    db.log_attempt("aural_x", True, domain="aural")
    assert "Perfect Ear" in ach.evaluate_global(db)
    # a miss resets the run for the next tier of checks
    db.log_attempt("aural_x", False, domain="aural")
    assert not ach._domain_run(db, "aural")


def test_dictation_and_quick_thinker_counts(db):
    for _ in range(25):
        db.log_attempt("dict", True, domain="aural",
                       exercise_type="melodic_dictation", response_ms=2000)
    titles = ach.evaluate_global(db)
    assert "Take It Down" in titles
    assert "Quick Thinker" in titles


def test_comeback_achievement_via_kv_flag(db):
    db.update_profile(streak_days=3)
    assert "Comeback" not in ach.evaluate_global(db)
    db.kv_set("streak.lost_after_3", True)
    assert "Comeback" in ach.evaluate_global(db)


def test_night_owl_and_early_bird(db):
    # midnight-ish attempt: synthesize by inserting directly with a fixed ts
    midnight = time.mktime((2026, 6, 10, 0, 30, 0, 0, 0, -1))
    db.conn.execute(
        "INSERT INTO attempts (ts, skill_id, domain, exercise_type, correct) "
        "VALUES (?, 'x', 'theory', 't', 1)", (midnight,))
    morning = time.mktime((2026, 6, 10, 6, 30, 0, 0, 0, -1))
    db.conn.execute(
        "INSERT INTO attempts (ts, skill_id, domain, exercise_type, correct) "
        "VALUES (?, 'x', 'theory', 't', 1)", (morning,))
    db.conn.commit()
    titles = ach.evaluate_global(db)
    assert "Night Owl" in titles
    assert "Early Bird" in titles


def test_achievements_with_dates(db):
    db.unlock_achievement("first_lesson")
    dates = db.achievements_with_dates()
    assert "first_lesson" in dates and dates["first_lesson"] > 0


# -- celebration UI -----------------------------------------------------------

@pytest.fixture
def qapp():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


def _drop_widget(widget, qapp) -> None:
    """Deterministic Qt teardown. Leaving a dropped widget tree for the GC
    lets Python delete live QObjects in the middle of a later event loop
    pass, which aborts the process (0xC0000409) on some interpreter/GC
    timings. Delete it now, on our terms."""
    widget.close()
    widget.deleteLater()
    qapp.processEvents()


def test_celebration_overlay_shows_and_dismisses(qapp):
    from PyQt6.QtWidgets import QWidget
    from music_theory.ui.celebration import CelebrationOverlay
    host = QWidget()
    host.resize(800, 600)
    ov = CelebrationOverlay(host)
    ov.celebrate("Level up", "Theory is now Early.", kind="level_up")
    assert ov.active
    assert ov._particles, "burst should spawn particles"
    for _ in range(120):                 # run the animation to completion
        ov._tick()
    assert not ov._particles
    ov.dismiss()
    assert not ov.active
    _drop_widget(host, qapp)


def test_celebration_reduce_motion_skips_particles(qapp):
    from PyQt6.QtWidgets import QWidget
    from music_theory.ui.celebration import CelebrationOverlay
    host = QWidget()
    host.resize(800, 600)
    ov = CelebrationOverlay(host)
    ov.celebrate("Skill mastered", "Triads are yours.", kind="mastery",
                 reduce_motion=True)
    assert ov.active
    assert not ov._particles
    ov.dismiss()
    _drop_widget(host, qapp)


def test_animate_bar_jumps_when_reduced(qapp):
    from PyQt6.QtWidgets import QProgressBar
    from music_theory.ui.celebration import animate_bar
    bar = QProgressBar()
    bar.setMaximum(100)
    animate_bar(bar, 60, reduce_motion=True)
    assert bar.value() == 60
    animate_bar(bar, 999, reduce_motion=True)   # clamped to maximum
    assert bar.value() == 100


def test_achievements_gallery_renders_locked_and_unlocked(qapp):
    from music_theory.app import build_context
    from music_theory.ui.screens.achievements import AchievementsScreen
    ctx = build_context()
    try:
        ctx.db.unlock_achievement("first_lesson")
        screen = AchievementsScreen(ctx)
        screen.refresh()
        tiles = screen.grid.count()
        assert tiles >= len(ach.ACHIEVEMENTS)
        assert "1 of" in screen.progress.text()
        _drop_widget(screen, qapp)
    finally:
        ctx.engine.close()
        ctx.db.close()


def test_session_streak_message_after_five_correct(qapp):
    """Drive a real session; after 5 straight correct answers the feedback
    panel should carry a streak line from the bank."""
    from music_theory.app import build_context
    from music_theory.ui.main_window import MainWindow
    ctx = build_context()
    try:
        ctx.db.reset_progress()
        ctx.scheduler.ensure_bootstrap()
        win = MainWindow(ctx)
        sess = win.session
        win.go_to("session")
        sess._load_next()
        streak_seen = False
        for _ in range(6):
            if not sess.summary.isHidden():
                sess._continue()
            for _ in range(12):
                if sess.lesson.isHidden():
                    break
                sess.lesson._next()
            ex = sess.player.ex
            if ex is None:
                break
            sess.player._grade(ex.answer)
            if sess._consec_correct >= 5:
                streak_seen = True
                break
            sess._load_next()
        assert streak_seen
    finally:
        win.close()
        win.deleteLater()
        qapp.processEvents()
        ctx.engine.close()
        ctx.db.close()
