"""Reference screen (circle of fifths, explorer, glossary) and practice/
session flow polish. Generators added in the same batch are auto-covered by
the parametrized suite in test_generators.py."""

from __future__ import annotations

import pytest

pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def ctx():
    from music_theory.app import build_context
    c = build_context()
    yield c
    c.engine.close()
    c.db.close()


def test_circle_of_fifths_selection_updates_key_card(qapp, ctx):
    from music_theory.ui.screens.reference import _CIRCLE, ReferenceScreen
    screen = ReferenceScreen(ctx)
    assert "C major" in screen.key_title.text()
    screen.circle.selected = 3                       # A major
    screen._on_key_picked(3)
    assert "A major" in screen.key_title.text()
    assert "3" in screen.key_info.text()             # 3 sharps
    assert screen.key_staff.key_sig["count"] == 3
    assert len(_CIRCLE) == 12


def test_circle_click_hits_a_segment(qapp, ctx):
    from PyQt6.QtCore import QPointF, Qt
    from PyQt6.QtGui import QMouseEvent
    from music_theory.ui.screens.reference import ReferenceScreen
    screen = ReferenceScreen(ctx)
    screen.circle.resize(400, 400)
    # click at 3 o'clock mid-ring = 90 degrees clockwise from C = E major (idx 4)
    ev = QMouseEvent(QMouseEvent.Type.MouseButtonPress, QPointF(200 + 160, 200),
                     Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton,
                     Qt.KeyboardModifier.NoModifier)
    screen.circle.mousePressEvent(ev)
    assert screen.circle.selected == 3 or screen.circle.selected == 4  # boundary-safe


def test_explorer_renders_scale_and_chord(qapp, ctx):
    from music_theory.ui.screens.reference import ReferenceScreen
    screen = ReferenceScreen(ctx)
    screen.ex_root.setCurrentText("D")
    screen.ex_kind.setCurrentIndex(1)                # scale/mode
    screen.ex_sub.setCurrentIndex(0)
    screen._explore()
    assert len(screen.ex_staff.notes) >= 7
    screen.ex_kind.setCurrentIndex(2)                # triad
    screen.ex_sub.setCurrentIndex(0)
    screen._explore()
    assert len(screen.ex_staff.notes) == 3


def test_glossary_filter(qapp, ctx):
    from music_theory.ui.screens.reference import GLOSSARY, ReferenceScreen
    screen = ReferenceScreen(ctx)
    assert len(GLOSSARY) >= 30
    screen._filter_glossary("tritone")
    visible = [row for _, row in screen._gloss_rows if not row.isHidden()]
    hidden = [row for _, row in screen._gloss_rows if row.isHidden()]
    assert visible and hidden
    screen._filter_glossary("")
    assert all(not row.isHidden() for _, row in screen._gloss_rows)


def test_glossary_examples_play_without_error(qapp, ctx):
    from music_theory.ui.screens.reference import GLOSSARY, ReferenceScreen
    screen = ReferenceScreen(ctx)
    for _term, _definition, play in GLOSSARY:
        if play:
            screen._play_example(play)               # guard: must never raise


def test_practice_focus_weakest_presets_topic(qapp, ctx):
    from music_theory.ui.screens.practice import PracticeScreen
    screen = PracticeScreen(ctx)
    screen._focus_weakest()
    assert screen.type_combo.currentData()           # some etype selected
    assert screen.player.ex is not None


def test_session_recap_lists_skills(qapp, ctx):
    from music_theory.ui.screens.session import SessionScreen
    screen = SessionScreen(ctx)
    screen.lesson_n = 10
    screen.lesson_correct = 7
    screen.lesson_skill_stats = {"fund.note_names": [6, 5], "fund.intervals": [4, 2]}
    screen.lesson_skills = set(screen.lesson_skill_stats)
    screen._show_summary()
    assert not screen.summary.isHidden()
    labels = [w.text() for w in screen.summary.findChildren(type(screen.skill_label))]
    joined = " ".join(labels)
    assert "Note Names" in joined
    assert "Worth another look" in joined
