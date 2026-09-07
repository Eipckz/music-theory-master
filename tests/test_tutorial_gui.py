"""Protect real assignment data and action-gated onboarding transitions."""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PyQt6.QtWidgets import QApplication

from music_theory.theory.part_writing.models import Voice
from music_theory.theory.pitch import Note
from music_theory.ui.screens.tutorial import TutorialScreen, TutorialStore


@pytest.fixture
def tour(db, settings):
    app = QApplication.instance() or QApplication([])
    ctx = SimpleNamespace(db=db, settings=settings, engine=Mock(), midi=None)
    screen = TutorialScreen(ctx)
    yield screen
    screen.close(); screen.deleteLater(); app.processEvents()


def test_training_edits_never_replace_assignment(tour):
    original = {"sentinel": "the learner's actual assignment"}
    tour.ctx.db.kv_set("part_writing.autosave", original)
    tour.start(restart=True)
    assert isinstance(tour.lab.ctx.db, TutorialStore)
    tour.validate()
    assert not tour.next_btn.isEnabled()
    tour.lab._choose_voice(Voice.BASS); tour.validate(); tour.advance()
    assert tour.step == 1
    tour.lab._staff_note(0, Voice.BASS, Note.parse("D3")); tour.validate()
    assert not tour.next_btn.isEnabled()
    assert "D3" in tour.feedback.text()
    tour.lab._staff_note(0, Voice.BASS, Note.parse("C3")); tour.validate()
    assert tour.next_btn.isEnabled()
    tour.advance()
    assert tour.step == 2
    assert tour.ctx.db.kv_get("part_writing.autosave") == original
    tour.start()
    assert tour.step == 2
    assert tour.lab.problem.slots[0].voice(Voice.BASS).pitch.exact.name == "C3"


def test_tutorial_chrome_and_completion_survive_navigation(tour):
    tour.start(restart=True)
    tour.step = 6; tour.show_step()
    tour.lab.editor_tabs.setCurrentIndex(1); tour.validate()
    assert "7 / 7" in tour.lab.coach.kicker.text()
    assert tour.passed
    tour.advance()
    assert tour.ctx.db.kv_get("tutorial.harmony")["complete"]
    tour.leave()
    assert tour.ctx.db.kv_get("tutorial.harmony")["complete"]


def test_tutorial_store_returns_copies():
    store = TutorialStore(); original = {"notes": ["C3"]}
    store.kv_set("score", original)
    original["notes"].append("D3")
    read = store.kv_get("score"); read["notes"].clear()
    assert store.kv_get("score") == {"notes": ["C3"]}
