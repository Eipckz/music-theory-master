"""The built-in lesson system: content integrity, full curriculum coverage,
and the teach-then-drill flow in the Learn screen."""

from __future__ import annotations

import pytest

from music_theory.curriculum import CURRICULUM
from music_theory.curriculum.lessons import LESSONS, has_lesson, lesson_for

_PLAY_MODES = {"melody", "interval", "chord", "sequence", "harmonic", "note"}


def test_every_lesson_belongs_to_a_real_skill():
    for skill_id in LESSONS:
        assert CURRICULUM.get(skill_id) is not None, f"orphan lesson: {skill_id}"


def test_every_skill_has_a_lesson():
    """The Duolingo promise: no skill is ever drilled without teaching first."""
    missing = [s.id for s in CURRICULUM if not has_lesson(s.id)]
    assert not missing, f"skills without lessons: {missing}"


def test_lesson_pages_are_well_formed():
    for skill_id, pages in LESSONS.items():
        assert pages, f"{skill_id}: empty lesson"
        for page in pages:
            assert page.title and len(page.body) > 40, \
                f"{skill_id}: page '{page.title}' too thin to teach anything"
            if page.play:
                assert page.play.get("mode") in _PLAY_MODES, \
                    f"{skill_id}: unknown play mode {page.play.get('mode')!r}"


def test_lesson_audio_examples_render():
    """Every audio example must actually render on the synth backend."""
    from music_theory.audio.engine import AudioEngine
    from music_theory.exercises.base import render_play

    class _Settings:
        def get(self, key, default=None):
            return {"audio_backend": "synth"}.get(key, default)

    eng = AudioEngine(_Settings())
    try:
        for skill_id, pages in LESSONS.items():
            for page in pages:
                if page.play:
                    buf = render_play(eng, page.play)
                    assert buf is not None and buf.size > 0, \
                        f"{skill_id}: '{page.title}' audio failed to render"
    finally:
        eng.close()


def test_lesson_staff_notes_parse():
    from music_theory.theory.pitch import Note

    for skill_id, pages in LESSONS.items():
        for page in pages:
            if page.staff and isinstance(page.staff.get("notes"), str):
                for name in page.staff["notes"].split():
                    Note.parse(name)  # raises on a typo


# -- GUI flow ----------------------------------------------------------------
pytest.importorskip("PyQt6")


@pytest.fixture(scope="module")
def qapp():
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_first_encounter_teaches_then_drills(qapp):
    from music_theory.app import build_context
    from music_theory.ui.main_window import MainWindow

    ctx = build_context()
    ctx.db.reset_progress()
    ctx.scheduler.ensure_bootstrap()
    win = MainWindow(ctx)
    win.show()
    qapp.processEvents()
    try:
        sess = win.session
        win.go_to("session")
        qapp.processEvents()
        # A fresh learner's first skill must open with its lesson, not a quiz.
        assert not sess.lesson.isHidden()
        assert sess.player.isHidden()
        skill_id = sess.pick.skill_id
        # Page through to the end - the exercise then appears...
        for _ in range(12):
            if sess.lesson.isHidden():
                break
            sess.lesson._next()
            qapp.processEvents()
        assert sess.lesson.isHidden()
        assert not sess.player.isHidden()
        assert sess.player.ex is not None
        # ...and the skill is marked taught, so it will not re-teach.
        assert ctx.db.kv_get(f"taught.{skill_id}")
    finally:
        ctx.engine.close()
        ctx.db.close()


def test_lesson_view_navigation(qapp):
    from music_theory.ui.lesson_view import LessonView

    pages = lesson_for("fund.note_names")
    done = {"n": 0}
    view = LessonView(engine=None)
    view.set_lesson("Note Names", pages, on_done=lambda: done.__setitem__("n", 1))
    assert view.progress.text() == f"1 / {len(pages)}"
    for _ in range(len(pages) - 1):
        view._next()
    assert view.next_btn.text().startswith("Start practicing")
    view._next()
    assert done["n"] == 1
    view._back()  # back at the end must not crash
