"""Headless GUI smoke test: the whole app must boot and every screen render."""

from __future__ import annotations

import pytest

pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def window(qapp):
    from music_theory.app import build_context
    from music_theory.ui.main_window import MainWindow
    ctx = build_context()
    win = MainWindow(ctx)
    win.show()
    qapp.processEvents()
    yield win
    ctx.engine.close()
    ctx.db.close()


def test_all_screens_render(qapp, window):
    from music_theory.ui.main_window import _NAV
    for _label, name in _NAV:
        window.go_to(name)
        qapp.processEvents()
    assert window.stack.currentWidget() is not None


def test_session_answer_flow(qapp, window):
    sess = window.screens["session"]
    window.go_to("session")
    sess._load_next()
    answered = 0
    for i in range(12):
        if not sess.summary.isHidden():   # lessons end every 10 items with a summary
            sess._continue()
            qapp.processEvents()
        ex = sess.player.ex
        if ex is None:
            break
        sess.player._grade(ex.answer)
        sess._load_next()
        qapp.processEvents()
        answered += 1
    assert answered > 0
    assert sess.answered == answered and sess.correct == answered


def test_practice_and_dictation(qapp, window):
    window.go_to("dictation")
    qapp.processEvents()
    assert window.practice.player.ex.etype == "melodic_dictation"
    window.practice.preset(domain="theory", etype="triad_quality")
    qapp.processEvents()
    ex = window.practice.player.ex
    window.practice.player._grade(ex.answer)
    qapp.processEvents()
    assert window.practice.player._answered
