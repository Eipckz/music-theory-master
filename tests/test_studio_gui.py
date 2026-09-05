from types import SimpleNamespace
from unittest.mock import Mock
import sys
import time

import numpy as np
import pytest
from PyQt6.QtWidgets import QApplication, QFileDialog
from music_theory.audio.recording import MicrophoneRecorder
from music_theory.ui.screens.studio import StudioScreen


@pytest.fixture
def app():
    instance = QApplication.instance() or QApplication([])
    yield instance
    instance.processEvents()


@pytest.fixture
def studio(app):
    from music_theory.storage import Settings
    engine = Mock()
    page = StudioScreen(SimpleNamespace(engine=engine, midi=None, settings=Settings()))
    page.resize(940, 700)
    page.show()
    yield page
    page.close()
    page.deleteLater()
    app.processEvents()


def test_microphone_capture_bound_and_device_cleanup(monkeypatch):
    stream = Mock()
    fake = SimpleNamespace(query_devices=lambda *a: {"default_samplerate": 16000}, InputStream=Mock(return_value=stream))
    monkeypatch.setitem(sys.modules, "sounddevice", fake)
    recorder = MicrophoneRecorder()
    recorder.start(seconds=1)
    recorder._callback(np.ones((20000, 1)), 20000, None, "")
    samples, sr = recorder.stop()
    assert len(samples) == 16000 and sr == 16000
    stream.close.assert_called_once()
    assert recorder.stream is None


def test_singing_wav_analysis_and_stale_results(studio, app):
    page = studio.singing
    studio.tabs.setCurrentWidget(page)
    t = np.arange(16000) / 16000
    page.samples, page.rate = .3 * np.sin(2 * np.pi * 440 * t), 16000
    page.analyze()
    deadline = time.monotonic() + 5
    while page.future is not None and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(.01)
    assert "Within" in page.report.toPlainText() and page.frames
    page.target.setText("B4")
    assert not page.frames and "changed" in page.report.toPlainText()
    page.recorder.stream = Mock()
    stream = page.recorder.stream
    studio.tabs.setCurrentWidget(studio.jazz)
    app.processEvents()
    assert page.recorder.stream is None and stream.close.called


def test_assignment_ui_round_trip(studio, tmp_path, monkeypatch):
    page = studio.assignments
    studio.tabs.setCurrentWidget(page)
    page.count.setValue(2)
    page.create()
    assert len(page.exercises) == 2
    assignment_path = tmp_path / "assignment.json"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a: (str(assignment_path), ""))
    page.save()
    assert assignment_path.exists()
    page.start()
    for ex in page.exercises:
        page.player._grade(ex.answer)
        page.advance()
    assert "2/2" in page.report.toPlainText()
    result_path = tmp_path / "result.json"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a: (str(result_path), ""))
    page.export()
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a: (str(result_path), ""))
    page.check()
    assert "Regraded" in page.report.toPlainText() and "2/2" in page.report.toPlainText()


def test_score_import_practice_and_jazz_playback(studio, tmp_path):
    from music21 import stream, note
    score = stream.Score()
    part = stream.Part()
    for name in ("C4", "D4", "E4"):
        part.append(note.Note(name))
    score.append(part)
    path = tmp_path / "melody.musicxml"
    score.write("musicxml", fp=path)
    page = studio.score
    page.load(path)
    assert page.score is not None
    page.practice()
    assert page.player.ex.answer == [60, 62, 64]
    page.send_singing()
    assert len(studio.singing.expected) == 3
    page.review()
    assert "No findings" in page.report.toPlainText()
    studio.jazz.play()
    assert studio.jazz.ctx.engine.play_sequence.called
