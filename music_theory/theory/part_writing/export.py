"""Lazy MusicXML export for four independent, spelled voices."""

from __future__ import annotations

from pathlib import Path

from ..pitch import Note
from ..scales import key_fifths
from .models import Clef, PartWritingProblem, PartWritingSolution, Voice, VOICE_ORDER


_DEFAULT_CLEFS = {
    Voice.SOPRANO: Clef.TREBLE,
    Voice.ALTO: Clef.TREBLE,
    Voice.TENOR: Clef.BASS,
    Voice.BASS: Clef.BASS,
}


def _m21():
    import music21  # noqa: WPS433 - heavy dependency must remain lazy
    return music21


def _clef(m21, clef: Clef):
    return {
        Clef.TREBLE: m21.clef.TrebleClef,
        Clef.BASS: m21.clef.BassClef,
        Clef.ALTO: m21.clef.AltoClef,
        Clef.TENOR: m21.clef.TenorClef,
    }[clef]()


def _voice_clef(problem: PartWritingProblem, voice: Voice) -> Clef:
    for slot in problem.slots:
        if slot.voice(voice).clef is not None:
            return slot.voice(voice).clef
    return _DEFAULT_CLEFS[voice]


def _music21_pitch(note: Note) -> str:
    return note.m21_name


def to_music21_score(problem: PartWritingProblem, solution: PartWritingSolution):
    m21 = _m21()
    score = m21.stream.Score(id="PartWritingScore")
    score.metadata = m21.metadata.Metadata()
    score.metadata.title = problem.title
    names = {
        Voice.SOPRANO: "Soprano", Voice.ALTO: "Alto",
        Voice.TENOR: "Tenor", Voice.BASS: "Bass",
    }
    fifths = key_fifths(Note.parse(problem.key_tonic + "4"), problem.mode)
    for voice in VOICE_ORDER:
        part = m21.stream.Part(id=names[voice])
        part.partName = names[voice]
        part.insert(0, _clef(m21, _voice_clef(problem, voice)))
        part.insert(0, m21.key.KeySignature(fifths))
        part.insert(0, m21.meter.TimeSignature(f"{problem.meter[0]}/{problem.meter[1]}"))
        for index, (slot, voicing) in enumerate(zip(problem.slots, solution.voicings)):
            offset = part.highestTime
            note = m21.note.Note(_music21_pitch(voicing[voice]))
            note.duration.quarterLength = float(slot.duration)
            if voice == Voice.SOPRANO:
                label = (solution.harmony_labels[index]
                         if index < len(solution.harmony_labels)
                         else slot.harmony.roman_numeral or slot.harmony.chord_symbol or "")
                figure = slot.harmony.figured_bass or ""
                if label:
                    expression = m21.expressions.TextExpression(label)
                    expression.placement = "below"
                    part.insert(offset, expression)
                if figure:
                    note.lyric = figure
            part.append(note)
        score.append(part)
    return score


def export_musicxml(path: str | Path, problem: PartWritingProblem,
                    solution: PartWritingSolution) -> Path:
    destination = Path(path)
    if destination.suffix.lower() not in {".musicxml", ".xml", ".mxl"}:
        destination = destination.with_suffix(".musicxml")
    destination.parent.mkdir(parents=True, exist_ok=True)
    score = to_music21_score(problem, solution)
    score.write("musicxml", fp=str(destination))
    if not destination.exists() or destination.stat().st_size == 0:
        raise OSError(f"MusicXML export did not create {destination}")
    return destination
