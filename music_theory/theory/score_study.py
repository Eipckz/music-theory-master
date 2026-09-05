"""Bounded local MusicXML import, passage playback and voice-leading evidence."""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from pathlib import Path, PurePosixPath
import math
import zipfile

from defusedxml import ElementTree as SafeET

from .pitch import Note

MAX_XML = 8 * 1024 * 1024


@dataclass(frozen=True)
class ScoreEvent:
    part: str
    voice: str
    measure: int
    offset: float
    duration: float
    notes: tuple[Note, ...]


@dataclass(frozen=True)
class StudyScore:
    title: str
    parts: tuple[str, ...]
    events: tuple[ScoreEvent, ...]
    warnings: tuple[str, ...] = ()


def _xml_bytes(path: Path) -> bytes:
    if path.suffix.lower() not in (".xml", ".musicxml", ".mxl"):
        raise ValueError("Choose a local .musicxml, .xml or .mxl file.")
    if path.stat().st_size > MAX_XML:
        raise ValueError("Score files must be no larger than 8 MB.")
    if path.suffix.lower() != ".mxl":
        return path.read_bytes()
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        if len(entries) > 128 or sum(e.file_size for e in entries) > 2 * MAX_XML:
            raise ValueError("Compressed score exceeds the supported archive limits.")
        for entry in entries:
            name = PurePosixPath(entry.filename)
            if name.is_absolute() or ".." in name.parts or "\\" in entry.filename:
                raise ValueError("Invalid path inside the compressed score.")
            if entry.file_size > MAX_XML:
                raise ValueError("A compressed score member exceeds 8 MB.")
        container = SafeET.fromstring(archive.read("META-INF/container.xml"), forbid_dtd=True)
        roots = [e.attrib.get("full-path", "") for e in container.iter() if e.tag.split("}")[-1] == "rootfile"]
        if not roots or not roots[0]:
            raise ValueError("Compressed MusicXML has no score rootfile.")
        return archive.read(roots[0])


def load_score(path: Path) -> StudyScore:
    """Parse local bytes only; reject entities and strip DTDs before music21."""
    from music21 import converter, stream
    try:
        raw = _xml_bytes(Path(path))
        tree = SafeET.fromstring(raw, forbid_entities=True, forbid_external=True)
        if tree.tag.split("}")[-1] not in ("score-partwise", "score-timewise"):
            raise ValueError("This XML is not a MusicXML score.")
        tags = {e.tag.split("}")[-1] for e in tree.iter()}
        if sum(1 for e in tree.iter() if e.tag.split("}")[-1] == "note") > 6000:
            raise ValueError("Limit scores to 6,000 written note/rest elements.")
        parsed = converter.parseData(SafeET.tostring(tree, encoding="utf-8"), format="musicxml")
        parts = list(parsed.parts)
        if not 1 <= len(parts) <= 32:
            raise ValueError("Choose a score containing 1–32 parts.")
        events = []
        names = []
        warnings = ["Pitches are as written. Playback uses a constant selected tempo; repeats are not expanded."]
        if tags & {"repeat", "ending", "transpose", "grace", "unpitched", "ornaments"}:
            warnings.append("Repeat endings, instrument transposition, ornaments, grace notes and unpitched percussion are not realized by this practice player.")
        for index, original in enumerate(parts):
            part_name = f"{index + 1}: {original.partName or 'Part'}"
            names.append(part_name)
            part = original.stripTies(inPlace=False)
            for atom in part.recurse().notes:
                if atom.duration.isGrace or not hasattr(atom, "pitches"):
                    continue
                notes = []
                for p in atom.pitches:
                    alter = p.accidental.alter if p.accidental else 0
                    if not float(alter).is_integer() or not -2 <= alter <= 2:
                        raise ValueError("Microtones and accidentals beyond doubles are not supported.")
                    n = Note(p.step, int(alter), p.octave if p.octave is not None else 4)
                    if not 0 <= n.midi <= 127:
                        raise ValueError("A note is outside MIDI range 0–127.")
                    notes.append(n)
                if not notes:
                    continue
                duration = float(atom.quarterLength)
                offset = float(atom.getOffsetInHierarchy(part))
                if not math.isfinite(duration + offset) or not 0 < duration <= 256 or offset < 0:
                    raise ValueError("Unsupported duration or score offset.")
                voice = atom.getContextByClass(stream.Voice)
                voice_id = str(voice.id) if voice is not None else "1"
                events.append(ScoreEvent(part_name, voice_id, int(atom.measureNumber or 0), offset, duration, tuple(notes)))
        if not events:
            raise ValueError("This score has no supported pitched notes.")
        title = (parsed.metadata.title or parsed.metadata.movementName) if parsed.metadata else None
        title = str(title) if title else Path(path).stem
        return StudyScore(title, tuple(names), tuple(sorted(events, key=lambda e: (e.offset, e.part, e.voice))), tuple(warnings))
    except Exception as exc:
        raise ValueError(f"Could not import score: {exc}") from exc


def passage(score: StudyScore, parts: list[str], first: int, last: int) -> tuple[ScoreEvent, ...]:
    if first > last or not parts or any(p not in score.parts for p in parts):
        raise ValueError("Select score parts and a valid inclusive measure range.")
    events = tuple(e for e in score.events if e.part in parts and first <= e.measure <= last)
    if not events:
        raise ValueError("The selected passage contains no pitched notes.")
    return events


def playback_events(events: tuple[ScoreEvent, ...], bpm: int = 90) -> list[dict]:
    if not events or not 20 <= bpm <= 240:
        raise ValueError("Choose notes and a tempo between 20 and 240 BPM.")
    # Start at the first selected pitched attack; retain rests between attacks.
    start = min(e.offset for e in events)
    end = max(e.offset + e.duration for e in events)
    if (end - start) * 60 / bpm > 180:
        raise ValueError("Select a shorter passage: playback is limited to three minutes.")
    return [{"start": (e.offset - start) * 60 / bpm, "dur": max(.02, e.duration * 60 / bpm - .015),
             "midi": n.midi, "vel": 88} for e in events for n in e.notes]


def monophonic_line(events: tuple[ScoreEvent, ...]) -> tuple[ScoreEvent, ...]:
    ordered = tuple(sorted(events, key=lambda e: e.offset))
    if not ordered or any(len(e.notes) != 1 for e in ordered):
        raise ValueError("Select a single monophonic voice for melody practice.")
    if any(a.offset + a.duration > b.offset + 1e-6 for a, b in zip(ordered, ordered[1:])):
        raise ValueError("The selection contains overlapping voices; choose one voice.")
    return ordered


@dataclass(frozen=True)
class VoiceIssue:
    rule: str
    measure: int
    beat: float
    voices: str
    detail: str


def review_voice_leading(events: tuple[ScoreEvent, ...], *, leap_limit: int = 12) -> tuple[list[VoiceIssue], list[str]]:
    """Review independent lines; report evidence, not complete stylistic validity."""
    from music21 import interval, pitch
    if not 1 <= leap_limit <= 24:
        raise ValueError("Set melodic leap threshold between 1 and 24 semitones.")
    lines = {}
    for event in events:
        lines.setdefault((event.part, event.voice), []).append(event)
    issues, skipped = [], []
    valid = {}
    for key, atoms in lines.items():
        try:
            valid[key] = monophonic_line(tuple(atoms))
        except ValueError:
            skipped.append(f"{key[0]} / voice {key[1]}: polyphonic or overlapping line excluded.")
            continue
        for a, b in zip(valid[key], valid[key][1:]):
            if b.offset > a.offset + a.duration + 1e-6:
                continue
            distance = b.notes[0].midi - a.notes[0].midi
            if abs(distance) > leap_limit:
                issues.append(VoiceIssue("melodic_leap", b.measure, b.offset, f"{key[0]} / {key[1]}",
                                         f"{a.notes[0].name} → {b.notes[0].name}: {distance:+d} semitones"))
    for (ka, aa), (kb, bb) in combinations(valid.items(), 2):
        times = sorted({e.offset for e in aa + bb})
        prior = None
        ia = ib = 0
        for t in times:
            while ia + 1 < len(aa) and aa[ia + 1].offset <= t + 1e-6:
                ia += 1
            while ib + 1 < len(bb) and bb[ib + 1].offset <= t + 1e-6:
                ib += 1
            a, b = aa[ia], bb[ib]
            if not (a.offset <= t < a.offset + a.duration - 1e-6 and b.offset <= t < b.offset + b.duration - 1e-6):
                prior = None
                continue
            pa, pb = a.notes[0], b.notes[0]
            iv = interval.Interval(pitch.Pitch(pa.m21_name), pitch.Pitch(pb.m21_name))
            perfect = iv.specifier.name == "PERFECT" and iv.generic.simpleUndirected in (1, 5)
            if prior is not None:
                old_a, old_b, old_kind, old_end = prior
                da, db = pa.midi - old_a.midi, pb.midi - old_b.midi
                kind = iv.generic.simpleUndirected if perfect else 0
                if kind and kind == old_kind and da * db > 0 and t <= old_end + 1e-6:
                    label = "parallel_fifths" if kind == 5 else "parallel_octaves_unisons"
                    issues.append(VoiceIssue(label, a.measure, t, f"{ka[0]}/{ka[1]} ↔ {kb[0]}/{kb[1]}",
                        f"{old_a.name}–{old_b.name} → {pa.name}–{pb.name}; both voices move in the same direction"))
            prior = (pa, pb, iv.generic.simpleUndirected if perfect else 0, min(a.offset + a.duration, b.offset + b.duration))
    return issues, skipped
