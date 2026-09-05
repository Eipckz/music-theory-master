from pathlib import Path
import zipfile

import pytest

from music_theory.theory.pitch import Note
from music_theory.theory.score_study import (
    ScoreEvent, load_score, passage, playback_events, monophonic_line, review_voice_leading,
)


def event(part, offset, name, duration=1):
    return ScoreEvent(part, "1", 1 + int(offset // 4), offset, duration, (Note.parse(name),))


@pytest.fixture
def xml_score(tmp_path):
    from music21 import stream, note, meter, metadata
    score = stream.Score()
    score.metadata = metadata.Metadata(title="Practice fixture")
    for name, pitches in (("Upper", ["G4", "A4"]), ("Lower", ["C4", "D4"])):
        part = stream.Part()
        part.partName = name
        measure = stream.Measure(number=1)
        measure.append(meter.TimeSignature("4/4"))
        measure.append(note.Note(pitches[0], quarterLength=1))
        measure.append(note.Rest(quarterLength=1))
        measure.append(note.Note(pitches[1], quarterLength=2))
        part.append(measure)
        score.append(part)
    path = Path(tmp_path) / "score.musicxml"
    score.write("musicxml", fp=path)
    return path


def test_score_import_keeps_parts_and_internal_rest(xml_score):
    score = load_score(xml_score)
    assert score.title == "Practice fixture" and len(score.parts) == 2
    selected = passage(score, [score.parts[0]], 1, 1)
    assert [n.midi for e in selected for n in e.notes] == [67, 69]
    events = playback_events(selected, 120)
    assert events[0]["start"] == 0 and events[1]["start"] == 1
    assert len(monophonic_line(selected)) == 2
    with pytest.raises(ValueError, match="overlapping"):
        monophonic_line(score.events)


def test_compressed_score_no_disk_extraction(xml_score, tmp_path):
    archive = tmp_path / "score.mxl"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("META-INF/container.xml", '<container><rootfiles><rootfile full-path="music.xml"/></rootfiles></container>')
        z.writestr("music.xml", xml_score.read_bytes())
    assert len(load_score(archive).events) == 4
    assert not (tmp_path / "music.xml").exists()


def test_external_entities_are_rejected(tmp_path):
    path = tmp_path / "evil.xml"
    path.write_text('<!DOCTYPE score-partwise [<!ENTITY x SYSTEM "file:///secret">]><score-partwise>&x;</score-partwise>')
    with pytest.raises(ValueError):
        load_score(path)


def test_perfect_parallel_review_and_rests():
    notes = (event("Upper", 0, "G4"), event("Upper", 1, "A4"),
             event("Lower", 0, "C4"), event("Lower", 1, "D4"))
    issues, skipped = review_voice_leading(notes)
    assert not skipped and [i.rule for i in issues] == ["parallel_fifths"]
    # Parallel fourths do not trigger this check.
    fourths = (event("Upper", 0, "F4"), event("Upper", 1, "G4"),
               event("Lower", 0, "C4"), event("Lower", 1, "D4"))
    assert not review_voice_leading(fourths)[0]
    rests = (event("Upper", 0, "G4", .5), event("Upper", 2, "A4"),
             event("Lower", 0, "C4", .5), event("Lower", 2, "D4"))
    assert not review_voice_leading(rests)[0]


def test_polyphonic_line_exclusion_and_leap():
    poly = ScoreEvent("Chord", "1", 1, 0, 2, (Note.parse("C4"), Note.parse("E4")))
    issues, skipped = review_voice_leading((poly, event("Solo", 0, "C4"), event("Solo", 1, "D5")))
    assert skipped and issues[0].rule == "melodic_leap"
