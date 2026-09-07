"""Regressions for partial-score entry and clef-sensitive pitch placement.

These checks supplement the native Computer Use reviews in docs/design.
"""
from PyQt6.QtCore import QPoint, QPointF, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from music_theory.theory.part_writing.models import Voice
from music_theory.theory.pitch import Note
from music_theory.ui.widgets.satb_staff import SatbStaffWidget


def test_partial_score_clicks_cover_every_chord_and_bass_line():
    app = QApplication.instance() or QApplication([])
    staff = SatbStaffWidget(); staff.resize(900, 325)
    staff.set_score([], labels=["I", "IV", "V", "I"], partial=[{} for _ in range(4)])
    staff.set_selection(0, Voice.BASS); staff.show(); app.processEvents()
    entered = []
    staff.noteRequested.connect(lambda slot, voice, note: entered.append((slot, voice, note)))
    # The bass staff bottom is G2; ascending lines are B2, D3, F3, A3.
    for column, (y, pitch) in enumerate(((216, "G2"), (201, "B2"), (186, "D3"), (171, "F3"))):
        QTest.mouseClick(staff, Qt.MouseButton.LeftButton, pos=QPoint(round(staff._column_x(column)), y))
        assert entered[-1] == (column, Voice.BASS, Note.parse(pitch))
    staff.close()


def test_partial_notes_are_accessible_and_entry_respects_key_and_natural():
    app = QApplication.instance() or QApplication([])
    staff = SatbStaffWidget(); staff.resize(900, 325)
    staff.set_key("G", "major")
    staff.set_score([], labels=["I", "V"], partial=[{Voice.BASS: Note.parse("G2")}, {}])
    assert "bass G2" in staff.accessibleDescription()
    assert "soprano unknown" in staff.accessibleDescription()
    staff.set_selection(1, Voice.BASS)
    point = QPointF(staff._column_x(1), 171)
    assert staff._entry_at(point)[2] == Note.parse("F#3")
    staff.entry_accidental = 0
    assert staff._entry_at(point)[2] == Note.parse("F3")
    # Header/clef and opposite staff clicks must not produce extreme notes.
    assert staff._entry_at(QPointF(48, 171)) is None
    assert staff._entry_at(QPointF(staff._column_x(1), 36)) is None
    staff.show(); app.processEvents(); staff.close()


def test_delete_removes_selected_voice_without_replacing_other_voices():
    app = QApplication.instance() or QApplication([])
    staff = SatbStaffWidget(); staff.set_score([], labels=["I", "V"], partial=[{}, {}])
    staff.set_selection(1, Voice.TENOR); staff.show(); app.processEvents()
    removed = []
    staff.noteRemoved.connect(lambda slot, voice: removed.append((slot, voice)))
    QTest.keyClick(staff, Qt.Key.Key_Delete)
    assert removed == [(1, Voice.TENOR)]
    staff.close()


def test_piano_scale_and_chord_work_for_all_twelve_roots():
    from types import SimpleNamespace
    from unittest.mock import Mock
    from music_theory.ui.screens.piano_workspace import PianoWorkspaceScreen
    app = QApplication.instance() or QApplication([])
    engine = Mock()
    screen = PianoWorkspaceScreen(SimpleNamespace(engine=engine))
    for index, pitch_class in enumerate((0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11)):
        screen.root_combo.setCurrentIndex(index)
        screen._play_scale()
        scale = engine.play_melody.call_args.args[0]
        assert scale[0] == 60 + pitch_class
        assert scale[-1] == 72 + pitch_class
        screen._play_chord()
        assert engine.play_chord.call_args.args[0][0] == 60 + pitch_class
    screen.show(); app.processEvents(); screen.close()
