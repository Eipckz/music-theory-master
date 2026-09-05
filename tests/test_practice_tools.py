from pathlib import Path

import pytest

from music_theory.theory.practice_tools import (
    WORKSHEET_TYPES, export_melody, find_scales, fretboard, instrument_interval,
    metronome_events, tapped_bpm, transpose_notes, worksheet, worksheet_html,
)


def test_transposition_preserves_spelling_and_instrument_direction():
    assert [n.name for n in transpose_notes("C4 E4 G4", "M2")] == ["D4", "F#4", "A4"]
    assert [n.name for n in transpose_notes("Db4 F4", "m3", True)] == ["Bb3", "D4"]
    size, down = instrument_interval("Bb tenor sax", True)
    assert transpose_notes("C4", size, down)[0].name == "Bb2"
    size, down = instrument_interval("Bb tenor sax", False)
    assert transpose_notes("Bb2", size, down)[0].name == "C4"


def test_musicxml_roundtrip(tmp_path):
    from music21 import converter
    notes = transpose_notes("C4 Eb4 G4", "P5")
    path = Path(tmp_path) / "melody.musicxml"
    export_melody(path, notes)
    assert [n.pitch.midi for n in converter.parse(path).recurse().notes] == [67, 70, 74]


def test_scale_matches_and_outside_evidence():
    matches = find_scales("C D E F G A B", "C")
    assert matches[0].kind == "major"
    assert not matches[0].missing and not matches[0].outside
    assert not any(m.kind == "major" for m in find_scales("C Eb G", "C"))
    major = next(m for m in find_scales("C Eb G", "C", 1) if m.kind == "major")
    assert major.outside == (3,)
    assert find_scales("B# D## F##", "C")[0].outside == ()


def test_metronome_exact_positions_accents_and_triplets():
    events = metronome_events(120, "2+3", 3, 2)
    assert len(events) == 30
    assert events[3]["start"] == .5
    assert events[6]["midi"] == 82
    assert events[15]["midi"] == 88
    assert tapped_bpm([0, .5, 1, 1.5]) == 120
    assert tapped_bpm([0]) is None
    assert tapped_bpm([0, 12]) is None


def test_custom_tuning_and_capo():
    board = fretboard("E2 A2 D3 G3 B3 E4", 12, 2)
    assert board[0][0].midi == 42
    assert board[0][12].midi == 54
    assert board[-1][0].midi == 66
    assert fretboard("G4 C4 E4 A4")[0][0].midi > fretboard("G4 C4 E4 A4")[1][0].midi


@pytest.mark.parametrize("kind", WORKSHEET_TYPES)
def test_worksheet_printable_answers_and_reproducibility(kind):
    one = worksheet([kind], 5, 3, 1234)
    two = worksheet([kind], 5, 3, 1234)
    assert [e.prompt for e in one] == [e.prompt for e in two]
    assert all(e.grade(e.answer) and e.explanation for e in one)
    assert "Answer key" not in worksheet_html(one)
    assert "Answer key" in worksheet_html(one, answers=True)
    assert "&lt;script&gt;" in worksheet_html(one, title="<script>")
    if kind == "interval_construction":
        assert all(e.tags["staff_prompt"]["notes"][0].name in e.prompt for e in one)


@pytest.mark.parametrize("call", [lambda: transpose_notes("C4", "P3"),
                                 lambda: transpose_notes("G9", "P8"),
                                 lambda: find_scales("H"),
                                 lambda: metronome_events(0, "4", 1, 1),
                                 lambda: metronome_events(90, "2++3", 1, 1),
                                 lambda: fretboard("C9", 24),
                                 lambda: worksheet(["melodic_dictation"], 4, 3, 0)])
def test_invalid_inputs(call):
    with pytest.raises(ValueError):
        call()
