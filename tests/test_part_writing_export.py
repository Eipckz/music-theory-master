"""MusicXML export retains four parts, spelling, rhythm, labels, and clefs."""

from __future__ import annotations

from music_theory.theory.part_writing.export import export_musicxml, to_music21_score
from music_theory.theory.part_writing.models import (
    Clef, HarmonyConstraint, HarmonySlot, PartWritingProblem,
    PartWritingSolution, Voice, Voicing,
)
from music_theory.theory.pitch import Note


def V(s, a, t, b):
    return Voicing(*(Note.parse(name) for name in (s, a, t, b)))


def export_fixture():
    slots = [HarmonySlot(HarmonyConstraint(roman_numeral="I"), duration=1.0),
             HarmonySlot(HarmonyConstraint(roman_numeral="V7", figured_bass="7"),
                         duration=2.0)]
    slots[0].voice(Voice.SOPRANO).clef = Clef.TREBLE
    slots[0].voice(Voice.ALTO).clef = Clef.ALTO
    slots[0].voice(Voice.TENOR).clef = Clef.TENOR
    slots[0].voice(Voice.BASS).clef = Clef.BASS
    problem = PartWritingProblem(
        key_tonic="Bb", meter=(3, 4), slots=slots, title="Spelled SATB")
    solution = PartWritingSolution(
        [V("Bb4", "F4", "D4", "Bb2"), V("A4", "Eb4", "C4", "F2")],
        0.0, harmony_labels=["I", "V7"])
    return problem, solution


def test_music21_score_has_four_named_parts_and_requested_clefs():
    problem, solution = export_fixture()
    score = to_music21_score(problem, solution)
    assert score.metadata.title == "Spelled SATB"
    assert [part.partName for part in score.parts] == ["Soprano", "Alto", "Tenor", "Bass"]
    assert [part.recurse().getElementsByClass("Clef").first().name
            for part in score.parts] == ["treble", "alto", "tenor", "bass"]
    assert score.parts[0].recurse().notes[0].pitch.nameWithOctave == "B-4"
    assert [float(note.duration.quarterLength)
            for note in score.parts[0].recurse().notes] == [1.0, 2.0]


def test_exported_musicxml_reopens_with_labels_and_spelled_pitches(tmp_path):
    from music21 import converter

    problem, solution = export_fixture()
    path = export_musicxml(tmp_path / "satb", problem, solution)
    assert path.suffix == ".musicxml" and path.stat().st_size > 1000
    restored = converter.parse(str(path))
    assert len(restored.parts) == 4
    assert restored.parts[0].recurse().notes[0].pitch.nameWithOctave == "B-4"
    from music21 import expressions as m21_expressions
    expressions = [str(expression.content) for expression in
                   restored.parts[0].recurse().getElementsByClass(
                       m21_expressions.TextExpression)]
    assert "I" in expressions and "V7" in expressions
    assert restored.parts[0].recurse().notes[1].lyric == "7"
