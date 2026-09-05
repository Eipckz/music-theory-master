"""Pre-graduate bridge: theory math, curriculum wiring, generators, and UI."""

from __future__ import annotations

import random

import pytest

from music_theory.curriculum import CURRICULUM, LEVEL_ORDER
from music_theory.exercises.registry import generate
from music_theory.theory.settheory import (
    interval_class, parse_pitch_classes, pc_label, pc_name,
)
from music_theory.theory.twelvetone import row_matrix


BRIDGE_TYPES = (
    "pitch_class_conversion",
    "pitch_class_clock",
    "interval_class_identification",
    "posttonal_interval_ear",
    "pcset_cardinality_ear",
    "plr_transformation_ear",
    "play_pitch_class_set",
    "play_row_segment",
    "play_plr_transform",
)


def test_pitch_class_entry_supports_numbers_te_and_note_names():
    assert parse_pitch_classes("{0, 4, 7, T, E}") == [0, 4, 7, 10, 11]
    assert parse_pitch_classes("C E G Bb") == [0, 4, 7, 10]
    assert parse_pitch_classes("C# Db", unique=False) == [1, 1]
    assert pc_label(10) == "T"
    assert pc_label(11) == "E"
    assert pc_name(10, prefer_flats=True) == "Bb"


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [(0, 1, 1), (0, 11, 1), (0, 5, 5), (0, 7, 5), (2, 8, 6)],
)
def test_interval_class_uses_shortest_clock_distance(a, b, expected):
    assert interval_class(a, b) == expected
    assert interval_class(b, a) == expected


def test_known_twelve_tone_matrix_is_consistent():
    row = [0, 1, 4, 2, 7, 3, 9, 5, 11, 6, 10, 8]
    matrix = row_matrix(row)
    assert len(matrix) == 12
    assert all(len(line) == 12 for line in matrix)
    assert matrix[0] == row
    assert sorted(line[0] for line in matrix) == list(range(12))


def test_pregraduate_level_sits_between_advanced_and_graduate():
    assert LEVEL_ORDER == [
        "Beginner", "Early", "Intermediate", "Advanced", "Pre-Graduate", "Graduate"
    ]
    assert CURRICULUM.get("posttonal.pitch_classes").level == "Pre-Graduate"
    assert CURRICULUM.get("aural.pc_collections").level == "Pre-Graduate"
    assert CURRICULUM.get("piano.row_realization").level == "Pre-Graduate"
    assert CURRICULUM.get("analysis.schenker").level == "Graduate"


def test_bridge_prerequisites_scaffold_instead_of_jump():
    pitch_classes = CURRICULUM.get("posttonal.pitch_classes")
    interval_classes = CURRICULUM.get("posttonal.interval_classes")
    row = CURRICULUM.get("posttonal.twelve_tone")
    assert "harmony.chromatic" in pitch_classes.prereqs
    assert interval_classes.prereqs == ("posttonal.pitch_classes",)
    assert {"posttonal.transforms", "posttonal.interval_classes"} <= set(row.prereqs)


@pytest.mark.parametrize("etype", BRIDGE_TYPES)
def test_bridge_generators_are_self_consistent_and_teach(etype):
    for difficulty in (4.0, 7.0, 10.0):
        ex = generate(etype, difficulty, random.Random(42 + int(difficulty)))
        assert ex.grade(ex.answer)
        assert ex.teach
        assert ex.hint
        assert ex.skill_id.startswith(("posttonal.", "aural.", "piano."))


def test_bridge_has_real_aural_and_keyboard_work():
    aural = generate("posttonal_interval_ear", 7.0, random.Random(1))
    collection = generate("pcset_cardinality_ear", 7.0, random.Random(2))
    piano = generate("play_pitch_class_set", 7.0, random.Random(3))
    row = generate("play_row_segment", 7.0, random.Random(4))
    assert aural.domain == collection.domain == "aural"
    assert aural.play and collection.play
    assert piano.domain == row.domain == "piano"
    assert piano.tags["match"] == row.tags["match"] == "pc"


pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def ctx(qapp):
    from music_theory.app import build_context
    context = build_context()
    context._screens = []
    yield context
    for widget in context._screens:
        widget.close()
        widget.deleteLater()
    qapp.processEvents()
    context.engine.close()
    context.db.close()


def _track(ctx, widget):
    ctx._screens.append(widget)
    return widget


def test_reference_posttonal_workbench_analyzes_transforms_and_builds_matrix(qapp, ctx):
    from music_theory.ui.screens.reference import ReferenceScreen
    screen = _track(ctx, ReferenceScreen(ctx))
    assert screen.tabs.tabText(2) == "Post-tonal bridge"
    screen.pc_input.setText("C E G")
    screen._post_analyze()
    assert "3-11" in screen.pc_result.text()
    assert "0 0 1 1 1 0" in screen.pc_result.text()
    screen.pc_op.setCurrentText("Tn")
    screen.pc_n.setValue(2)
    screen._post_transform()
    assert screen.pc_input.text() == "2 6 9"
    screen._post_build_matrix()
    assert screen.matrix_table.item(0, 0).text() == "0"
    assert screen.matrix_table.item(0, 11).text() == "8"
    screen.row_input.setText("0 0 1 2 3 4 5 6 7 8 9 T")
    screen._post_build_matrix()
    assert "exactly once" in screen.matrix_info.text()


def test_reference_clock_and_plr_have_accessible_live_state(qapp, ctx):
    from music_theory.ui.screens.reference import ReferenceScreen
    screen = _track(ctx, ReferenceScreen(ctx))
    screen.pc_clock.set_pcs([0, 3, 7])
    assert "0 C" in screen.pc_clock.accessibleDescription()
    screen.plr_start.setCurrentText("C")
    screen.plr_ops.setText("P")
    screen._post_apply_plr()
    assert "C → Cm" in screen.plr_result.text()


def test_piano_pregraduate_workspace_realizes_sets_rows_and_plr(qapp, ctx):
    from music_theory.ui.screens.piano_workspace import PianoWorkspaceScreen
    screen = _track(ctx, PianoWorkspaceScreen(ctx))
    assert screen.tabs.tabText(1) == "Pre-Graduate"
    screen.pg_set_input.setText("C E G")
    screen._play_pc_collection()
    assert "0=C" in screen.pg_readout.text()
    screen.pg_row_input.setText("0 1 4 2")
    screen._play_row_segment()
    assert "Ordered row" in screen.pg_readout.text()
    screen.pg_plr_start.setCurrentText("C")
    screen.pg_plr_ops.setText("R")
    screen._play_plr_path()
    assert "C → Am" in screen.pg_readout.text()
