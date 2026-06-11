"""Headless tests for the new learner-facing features: adaptive practice,
lesson structure with a completion summary, teaching feedback, hints, and
keyboard selection."""

from __future__ import annotations

import random

import pytest

pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QApplication, QPushButton

import music_theory.errors as errors
from music_theory.exercises.registry import generate
from music_theory.exercises.teaching import concept_for


def _skip_lesson(sess, qapp, max_pages: int = 12):
    """If the session is showing a first-time mini-lesson, page through it
    (what a learner does) so the exercise appears."""
    for _ in range(max_pages):
        if sess.lesson.isHidden():
            return
        sess.lesson._next()
        qapp.processEvents()


def _click_buttons(widget, *needles):
    clicked = 0
    for b in widget.findChildren(QPushButton):
        if any(n.lower() in b.text().lower() for n in needles):
            b.click()
            clicked += 1
    return clicked


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def window(qapp):
    from music_theory.app import build_context
    from music_theory.ui.main_window import MainWindow
    ctx = build_context()
    ctx.db.reset_progress()
    ctx.scheduler.ensure_bootstrap()
    win = MainWindow(ctx)
    win.show()
    qapp.processEvents()
    yield win
    # tear the widget tree down deterministically: dropping a live window
    # with running timers for the GC to find later is a use-after-free
    # (0xC0000409 mid-suite, timing dependent)
    win.close()
    win.deleteLater()
    qapp.processEvents()
    ctx.engine.close()
    ctx.db.close()


@pytest.fixture
def player(qapp):
    from music_theory.ui.exercise_player import ExercisePlayer
    return ExercisePlayer(engine=None, midi=None)


# -- lesson structure -----------------------------------------------------
def test_lesson_summary_after_ten_then_continue(qapp, window):
    from music_theory.ui.screens.session import LESSON_LEN
    sess = window.session
    window.go_to("session")
    qapp.processEvents()
    for _ in range(LESSON_LEN):
        _skip_lesson(sess, qapp)
        ex = sess.player.ex
        assert ex is not None
        sess.player._grade(ex.answer)
        sess._load_next()
        qapp.processEvents()
    assert not sess.summary.isHidden()      # summary is shown, not a crash
    assert sess.player.isHidden()
    sess._continue()
    qapp.processEvents()
    assert sess.summary.isHidden()
    assert sess.player.ex is not None       # a fresh lesson started


def test_advanced_learner_session_never_crashes(qapp, window):
    """Seed an advanced profile so roman-numeral content appears, then play many
    items: the old build closed the app here."""
    ctx = window.ctx
    for s in ctx.curriculum:
        if s.schedulable:
            ctx.db.upsert_mastery(s.id, rating=1520.0, mastery_prob=0.6,
                                  unlocked=1, n_attempts=5, n_correct=4)
    sess = window.session
    window.go_to("session")
    qapp.processEvents()
    done = 0
    for _ in range(40):
        if not sess.summary.isHidden():
            sess._continue()
        _skip_lesson(sess, qapp)
        ex = sess.player.ex
        if ex is None:
            sess._load_next()
            continue
        sess.player._grade(ex.answer)
        sess._load_next()
        qapp.processEvents()
        done += 1
    assert done >= 30


# -- adaptive practice ----------------------------------------------------
def test_practice_difficulty_rises_on_correct(qapp, window):
    p = window.practice
    window.go_to("practice")
    p.preset(domain="theory", etype="interval_identification")
    qapp.processEvents()
    start = p._adaptive_diff["interval_identification"]
    for _ in range(5):
        ex = p.player.ex
        p.player._grade(ex.answer)          # correct
        p.player._next()
        qapp.processEvents()
    assert p._adaptive_diff["interval_identification"] > start


def test_practice_difficulty_falls_on_wrong(qapp, window):
    p = window.practice
    window.go_to("practice")
    p.preset(domain="theory", etype="interval_identification")
    qapp.processEvents()
    p._adaptive_diff["interval_identification"] = 5.0
    p._new()
    qapp.processEvents()
    before = p._adaptive_diff["interval_identification"]
    ex = p.player.ex
    wrong = next(c for c in ex.choices if c != str(ex.answer))
    p.player._grade(wrong)
    qapp.processEvents()
    assert p._adaptive_diff["interval_identification"] < before


def test_practice_manual_override_when_adaptive_off(qapp, window):
    p = window.practice
    window.go_to("practice")
    p.preset(domain="theory", etype="triad_quality")
    p.adaptive_chk.setChecked(False)
    p.diff.setValue(14)  # 7.0
    p._new()
    qapp.processEvents()
    assert abs(p.player.ex.difficulty - 7.0) < 1e-6


# -- teaching feedback & hints -------------------------------------------
def test_wrong_answer_shows_concept(qapp, player):
    ex = generate("interval_recognition", 3.0, random.Random(0))
    player.set_exercise(ex, on_answer=lambda c, m: None)
    wrong = next(c for c in ex.choices if c != str(ex.answer))
    player._grade(wrong)
    text = player.feedback.text()
    assert "Not quite" in text
    assert str(ex.answer) in text
    assert concept_for("interval_recognition")[:24] in text


def test_correct_answer_is_concise(qapp, player):
    ex = generate("triad_quality", 2.0, random.Random(1))
    player.set_exercise(ex, on_answer=lambda c, m: None)
    player._grade(ex.answer)
    assert "Correct!" in player.feedback.text()


def test_hint_button_marks_hinted(qapp, player):
    ex = generate("interval_recognition", 3.0, random.Random(2))
    player.set_exercise(ex, on_answer=lambda c, m: None)
    assert player._hint_text  # this type has a hint
    player._show_hint()
    assert player.was_hinted
    assert player.hint_label.text()


def test_keyboard_number_selects_choice(qapp, player):
    ex = generate("triad_quality", 2.0, random.Random(3))
    captured = {}
    player.set_exercise(ex, on_answer=lambda c, m: captured.update(correct=c))
    player._choose_index(ex.choices.index(str(ex.answer)))
    assert player._answered
    assert captured.get("correct") is True


# -- regression: Qt 'clicked(bool)' must not trip the guard ---------------
def test_replay_and_next_buttons_do_not_trigger_guard(qapp, player):
    """Clicking Replay/Play/Next must run the slot, not surface the
    'Action interrupted' toast (the guard once forwarded Qt's checked bool)."""
    toasts = []
    errors.set_notifier(lambda title, msg: toasts.append((title, msg)))
    try:
        advanced = {"n": 0}
        ex = generate("interval_recognition", 3.0, random.Random(7))  # aural -> has audio
        player.set_exercise(ex, on_answer=lambda c, m: None,
                            on_next=lambda: advanced.__setitem__("n", advanced["n"] + 1))
        qapp.processEvents()
        assert _click_buttons(player, "Replay", "Play", "Listen") >= 1
        player._grade(ex.answer)
        qapp.processEvents()
        assert _click_buttons(player, "Next") == 1
        assert advanced["n"] == 1            # Next actually advanced
        assert toasts == []                  # and no error toast appeared
    finally:
        errors.set_notifier(None)
