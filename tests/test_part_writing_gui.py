"""Headless interaction tests for the complete Part Writing screen workflow."""

from __future__ import annotations

import time

import pytest

pytest.importorskip("PyQt6")

from PyQt6.QtCore import QItemSelectionModel, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from music_theory.theory.part_writing.models import (
    HarmonyConstraint, HarmonySlot, PartWritingProblem, PitchConstraint,
    Voice,
)
from music_theory.theory.pitch import Note


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(qapp):
    from music_theory.app import build_context
    from music_theory.ui.main_window import MainWindow
    ctx = build_context()
    win = MainWindow(ctx); win.show(); qapp.processEvents()
    yield win
    screen = win.screens["part_writing"]
    screen._stop_solve()
    wait_for_thread(qapp, screen)
    win.close(); win.deleteLater(); qapp.processEvents()
    ctx.engine.close(); ctx.db.close()


def wait_for_thread(qapp, screen, timeout=12.0):
    deadline = time.monotonic() + timeout
    while screen._thread is not None and time.monotonic() < deadline:
        qapp.processEvents()
        QTest.qWait(10)
    assert screen._thread is None


def part_writing(window, qapp):
    window.go_to("part_writing"); qapp.processEvents()
    return window.screens["part_writing"]


def test_navigation_edit_lock_and_slot_operations(window, qapp):
    screen = part_writing(window, qapp)
    assert window.stack.currentWidget() is screen
    index = screen.model.index(3, 0)
    assert screen.model.setData(index, "C5")
    screen.table.setCurrentIndex(index); screen._toggle_lock()
    assert screen.problem.slots[0].voice(Voice.SOPRANO).locked
    before = len(screen.problem.slots)
    screen._add_slot(); assert len(screen.problem.slots) == before + 1
    screen._remove_slot(); assert len(screen.problem.slots) == before


def test_keyboard_only_note_entry_and_multi_cell_piano_application(window, qapp):
    screen = part_writing(window, qapp); screen._reset()
    index = screen.model.index(3, 0)
    screen.table.setCurrentIndex(index); screen.table.setFocus()
    QTest.keyClick(screen.table, Qt.Key.Key_F2); qapp.processEvents()
    editor = qapp.focusWidget()
    QTest.keyClicks(editor, "C5"); QTest.keyClick(editor, Qt.Key.Key_Return)
    qapp.processEvents()
    assert screen.problem.slots[0].voice(Voice.SOPRANO).pitch.exact == Note.parse("C5")

    selection = screen.table.selectionModel()
    selection.clearSelection()
    for column in (1, 2):
        selection.select(screen.model.index(4, column),
                         QItemSelectionModel.SelectionFlag.Select)
    screen._piano_note(64)
    assert all(screen.problem.slots[column].voice(Voice.ALTO).pitch.exact == Note.parse("E4")
               for column in (1, 2))


def test_start_solve_display_and_move_between_solutions(window, qapp):
    screen = part_writing(window, qapp); screen._reset(); screen.top_k.setValue(3)
    screen._start_solve(); wait_for_thread(qapp, screen)
    assert len(screen.solutions) >= 2
    assert "zero hard-rule violations" in screen.diagnostics.toPlainText()
    first = screen.solution_index
    screen._next_solution(); assert screen.solution_index != first
    screen._previous_solution(); assert screen.solution_index == first
    solutions = screen.solutions
    screen.layout_box.setCurrentIndex(2)
    assert screen.solutions is solutions
    assert screen.staff.voicings == solutions[first].voicings
    screen.layout_box.setCurrentIndex(0)
    assert screen.solutions is solutions


def test_check_entered_solution_and_no_solution_diagnostics(window, qapp):
    screen = part_writing(window, qapp); screen._reset(); screen.top_k.setValue(1)
    screen._start_solve(); wait_for_thread(qapp, screen)
    answer = screen.solutions[0]
    for slot, voicing in zip(screen.problem.slots, answer.voicings):
        for voice in Voice:
            slot.voice(voice).pitch = PitchConstraint(exact=voicing[voice])
    screen.solutions = []
    screen._check(); qapp.processEvents()
    assert "Valid under the selected profile" in screen.status.text()

    screen._reset()
    screen.problem.slots[0].harmony.roman_numeral = "V"
    bass = screen.problem.slots[0].voice(Voice.BASS)
    bass.pitch = PitchConstraint(exact=Note.parse("B2")); bass.locked = True
    screen._start_solve(); wait_for_thread(qapp, screen)
    assert not screen.solutions
    assert "Locked bass contradicts" in screen.diagnostics.toPlainText()


def test_save_reopen_and_cancel_without_crash_when_navigating_away(window, qapp, tmp_path):
    screen = part_writing(window, qapp); screen._reset()
    screen.model.setData(screen.model.index(3, 0), "C5")
    path = tmp_path / "workflow.json"
    screen._save_to_path(path)
    screen.model.setData(screen.model.index(3, 0), "E5")
    screen._open_from_path(path)
    assert screen.problem.slots[0].voice(Voice.SOPRANO).pitch.exact == Note.parse("C5")

    labels = ("I", "IV", "V", "I") * 4
    screen.problem = PartWritingProblem(slots=[
        HarmonySlot(HarmonyConstraint(roman_numeral=label)) for label in labels])
    screen.model.replace_problem(screen.problem)
    screen._start_solve()
    window.go_to("dashboard"); qapp.processEvents()
    screen._stop_solve(); wait_for_thread(qapp, screen)
    assert window.stack.currentWidget() is window.screens["dashboard"]
