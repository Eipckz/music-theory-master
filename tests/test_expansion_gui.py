from types import SimpleNamespace
from unittest.mock import Mock
import random

import pytest
from PyQt6.QtWidgets import QApplication

from music_theory.adaptive.placement import PlacementTest
from music_theory.ui.screens.practice_tools import PracticeToolsScreen


@pytest.fixture
def app():
    app = QApplication.instance() or QApplication([])
    yield app
    app.processEvents()


def test_all_tools_interact_and_exports_are_separate(app, tmp_path, monkeypatch):
    from PyQt6.QtWidgets import QFileDialog
    engine = Mock()
    screen = PracticeToolsScreen(SimpleNamespace(engine=engine))
    screen.show()
    transpose, scales, metro, sheet, fret = [screen.tabs.widget(i) for i in range(5)]
    transpose.play()
    engine.play_melody.assert_called_once_with([62, 66, 69])
    destination = tmp_path / "transposed.musicxml"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a: (str(destination), ""))
    transpose.save()
    assert destination.exists()
    transpose.notes.setText("H4")
    assert not transpose.result and not transpose.save_btn.isEnabled()
    transpose.calculate()
    assert not transpose.result
    scales.tonic.setText("C")
    assert not scales.matches
    scales.calculate()
    assert scales.matches
    screen.tabs.setCurrentWidget(metro)
    metro.start()
    assert metro.running
    events = engine.play_events.call_args.args[0]
    assert events[0]["start"] == 0
    assert metro.finish_timer.isActive()
    screen.tabs.setCurrentWidget(sheet)
    app.processEvents()
    assert not metro.running
    assert not metro.finish_timer.isActive()
    assert engine.stop.called
    for answers in (False, True):
        destination = tmp_path / ("answers.html" if answers else "questions.html")
        monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, p=str(destination): (p, ""))
        sheet.save(answers)
        assert ("Answer key" in destination.read_text(encoding="utf-8")) == answers
    sheet.seed.setValue(7)
    assert not sheet.items and not sheet.save_questions.isEnabled()
    fret.play_cell(0, 0)
    engine.play_note.assert_called_with(40, dur=.6)
    fret.tuning.setText("bad")
    assert not fret.board and fret.table.rowCount() == 0
    screen.close()
    screen.deleteLater()


def test_comprehensive_placement_covers_tonal_and_rhythm_topics(db):
    pt = PlacementTest(comprehensive=True, rng=random.Random(11))
    while not pt.finished:
        ex = pt.next_item()
        assert pt.next_item() is ex
        pt.submit(True)
    result = pt.save(db)
    theory = {e["type"] for e in result["theory"]["evidence"]}
    assert {"modal_degree", "dominant_tendency", "chromatic_function", "modulation_evidence"} <= theory
    assert "rhythmic_dictation" in {e["type"] for e in result["aural"]["evidence"]}
    assert all(r["complete"] and r["topics"] >= 4 for r in result.values())
    assert db.kv_get("placement.evidence.theory")["items"] == result["theory"]["items"]


def test_placement_does_not_save_partial_or_inflate_retry(db, monkeypatch):
    import music_theory.adaptive.placement as module
    original = module.generate
    def only_easy(etype, difficulty, rng):
        if difficulty > 1:
            raise ValueError("simulate unavailable hard item")
        return original(etype, difficulty, rng)
    monkeypatch.setattr(module, "generate", only_easy)
    pt = PlacementTest(domains=["theory"], rng=random.Random(1))
    with pytest.raises(ValueError):
        pt.save(db)
    pt.next_item()
    assert pt._current[2] == .5
    pt.submit(True)
    assert pt.state["theory"].evidence[0]["difficulty"] == .5


def test_breadth_misses_lower_provisional_result():
    pt = PlacementTest(domains=["theory"], comprehensive=True, rng=random.Random(1))
    while not pt.finished:
        pt.next_item()
        pt.submit(pt.state["theory"].phase != "coverage")
    result = pt.results()["theory"]
    assert result["review"] and result["theta"] <= 8.5


def test_comprehensive_beginner_is_not_pushed_into_collegiate_questions():
    pt = PlacementTest(domains=["theory"], comprehensive=True, rng=random.Random(4))
    while not pt.finished:
        pt.next_item()
        pt.submit(False)
    result = pt.results()["theory"]
    assert result["theta"] == 0
    assert not any(e["type"] == "modulation_evidence" for e in result["evidence"])


def test_unrelated_fallback_cannot_be_credited(monkeypatch):
    import music_theory.adaptive.placement as module
    from music_theory.exercises.registry import generate
    monkeypatch.setattr(module, "generate", lambda *a: generate("note_identification", 0, random.Random(0)))
    pt = PlacementTest(domains=["aural"])
    with pytest.raises(ValueError, match="unrelated"):
        pt.next_item()
    assert pt._current is None and not pt.state["aural"].evidence
