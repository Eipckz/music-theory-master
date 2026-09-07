"""Regression coverage for complete notation in constrained viewports."""
import pytest
from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QPushButton
from music_theory.theory.pitch import Note
from music_theory.ui.widgets.staff import StaffWidget
from music_theory.ui.widgets.satb_staff import SatbStaffWidget
from music_theory.theory.part_writing.models import Voice

@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])

@pytest.mark.parametrize('clef', ['treble', 'bass', 'grand'])
@pytest.mark.parametrize('size', [(320, 110), (700, 240)])
def test_extreme_notes_and_long_sequences_fit(app, clef, size):
    staff = StaffWidget(clef)
    staff.line_spacing = 22
    staff.set_notes([24, 108] * 15, ghost=[20, 112] * 15)
    staff.resize(*size)
    staff.show()
    app.processEvents()
    visible = staff._view_transform.mapRect(staff._ink_bounds)
    assert QRectF(staff.rect()).adjusted(7, 7, -7, -7).contains(visible)
    staff.close()

def test_fitted_staff_click_uses_visible_pitch(app):
    staff = StaffWidget('bass')
    staff.resize(320, 110)
    staff.set_notes([24, 84])
    staff.allow_input = True
    staff.show()
    app.processEvents()
    note = Note.parse('C3')
    clef, bottom = staff._choose_clef(note)
    point = staff._view_transform.map(QPointF(180, staff._y_for(note, clef, bottom)))
    QTest.mouseClick(staff, Qt.MouseButton.LeftButton, pos=point.toPoint())
    assert staff.notes[-1] == note
    staff.close()

def test_solver_extreme_ledgers_fit(app):
    staff = SatbStaffWidget()
    staff.set_score([], partial=[{Voice.SOPRANO: Note.parse('C8'), Voice.BASS: Note.parse('C1')}])
    staff.resize(staff.minimumSizeHint())
    staff.show()
    app.processEvents()
    assert QRectF(staff.rect()).adjusted(7, 7, -7, -7).contains(staff._view_transform.mapRect(staff._ink_bounds))
    staff.close()

def test_short_exercise_scrolls_instead_of_squashing(app):
    from music_theory.ui.exercise_player import ExercisePlayer
    from music_theory.exercises.base import Exercise, InputMode
    player = ExercisePlayer()
    player.staff.line_spacing = 22
    player.set_exercise(Exercise('test', 'theory', 'roman', 'Identify this chord.',
        InputMode.MULTIPLE_CHOICE, 'i', choices=['i', 'iv', 'V', 'vi'],
        tags={'staff_prompt': {'notes': [48, 52, 55]}}))
    player.resize(500, 280)
    player.show()
    app.processEvents()
    assert player.scroll.verticalScrollBar().maximum() > 0
    assert player.staff.height() >= player.staff.minimumSizeHint().height()
    for button in player.input_host.findChildren(QPushButton):
        assert button.height() >= button.minimumSizeHint().height()
    player.close()
