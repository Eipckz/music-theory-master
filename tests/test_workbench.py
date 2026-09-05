from fractions import Fraction

import pytest

from music_theory.theory.workbench import analyze_notes, analyze_rhythm, duration


def test_spelling_and_tonal_context():
    midis, report = analyze_notes("G3 B3 D4 F4")
    assert midis == [55, 59, 62, 65]
    assert "V7 in C major" in report
    assert "Major Third, ascending" in report
    assert "Diminished Fourth" in analyze_notes("C#4 F4")[1]
    assert "Major Third" in analyze_notes("Db4 F4")[1]
    assert "descending" in analyze_notes("C5 G4")[1]


def test_extended_notes_and_incomplete_chord():
    assert len(analyze_notes("C3 E3 G3 Bb3 D4 F4 A4")[0]) == 7
    assert "insufficient information" in analyze_notes("C4 G4")[1]
    assert "440.00 Hz" in analyze_notes("A4")[1]
    assert analyze_notes("C E G")[0] == [60, 64, 67]


@pytest.mark.parametrize("text", ["", "H4", "C99", "C4 " * 65])
def test_invalid_notes(text):
    with pytest.raises(ValueError):
        analyze_notes(text)


@pytest.mark.parametrize("token, expected", [("h..", Fraction(7, 2)), ("t(e)", Fraction(1, 3)),
                                           ("rq.", Fraction(3, 2)), ("1/8", Fraction(1, 2))])
def test_durations(token, expected):
    assert duration(token) == expected


def test_meter_and_exact_triplets():
    bars, report = analyze_rhythm("t(e) t(e) t(e) q h | h.")
    assert bars[0].remaining == 0
    assert bars[1].remaining == 1
    assert "short by 1" in report
    assert "normally 2 beats" in analyze_rhythm("e e e e e e", "6/8")[1]
    assert "normally 3 beats" in analyze_rhythm("q q q", "3/4")[1]
    assert "over by 1" in analyze_rhythm("w q")[1]


@pytest.mark.parametrize("text,meter", [("q |", "4/4"), ("t(foo)", "4/4"), ("q", "0/4"),
                                     ("q", "4/0"), ("1/0", "4/4"), ("", "4/4")])
def test_invalid_rhythm(text, meter):
    with pytest.raises(ValueError):
        analyze_rhythm(text, meter)


def test_ui_invalidates_playback():
    from PyQt6.QtWidgets import QApplication
    from music_theory.ui.screens.workbench import Workbench
    app = QApplication.instance() or QApplication([])
    widget = Workbench(None)
    assert widget.play.isEnabled()
    widget.input.setText("bad")
    assert not widget.play.isEnabled()
    assert not widget.midis
    widget.calculate()
    assert "Input problem" in widget.report.toPlainText()
    rhythm = Workbench(None, rhythm=True)
    assert "complete" in rhythm.report.toPlainText()
    widget.close()
    rhythm.close()
    app.processEvents()
