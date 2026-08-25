"""Deterministic SATB candidate enumeration with early constraint pruning."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product

from ..pitch import Note
from .harmony import NormalizedHarmony, scale_degree
from .models import (
    ChordFactor, PartWritingProblem, Voice, VOICE_ORDER, Voicing,
)
from .profiles import RuleProfile
from .rules import validate_local


@dataclass(frozen=True)
class CandidateVoicing:
    voicing: Voicing
    local_score: float
    breakdown: tuple[tuple[str, float], ...]


_CACHE: dict[tuple, tuple[CandidateVoicing, ...]] = {}
_CACHE_MAX = 256


def clear_voicing_cache() -> None:
    _CACHE.clear()


def _note_pool(member: Note, low: int, high: int) -> list[Note]:
    out = []
    for octave in range(-1, 9):
        note = Note(member.letter, member.alter, octave)
        if low <= note.midi <= high:
            out.append(note)
    return out


def _matches_early(note: Note, voice, harmony: NormalizedHarmony,
                   problem: PartWritingProblem) -> bool:
    pitch = voice.pitch
    if pitch.exact is not None and note != pitch.exact:
        return False
    if pitch.pitch_class is not None \
            and note.name_no_octave != pitch.pitch_class.name_no_octave:
        return False
    if pitch.scale_degree is not None \
            and scale_degree(note, problem.key_tonic, problem.mode) != pitch.scale_degree:
        return False
    if pitch.chord_factor is not None and harmony.factor_for(note) != pitch.chord_factor:
        return False
    if pitch.allowed_pitches:
        exact = {item.name for item in pitch.allowed_pitches}
        classes = {item.name_no_octave for item in pitch.allowed_pitches}
        if note.name not in exact and note.name_no_octave not in classes:
            return False
    if pitch.minimum is not None and note.midi < pitch.minimum.midi:
        return False
    if pitch.maximum is not None and note.midi > pitch.maximum.midi:
        return False
    return True


def _constraint_signature(problem: PartWritingProblem, slot_index: int,
                          harmony: NormalizedHarmony, profile: RuleProfile) -> tuple:
    slot = problem.slots[slot_index]
    voices = []
    for voice in VOICE_ORDER:
        constraint = slot.voice(voice)
        pitch = constraint.pitch
        voices.append((
            voice.value,
            pitch.exact.name if pitch.exact else "",
            pitch.pitch_class.name_no_octave if pitch.pitch_class else "",
            pitch.scale_degree,
            pitch.chord_factor.value if pitch.chord_factor else "",
            tuple(note.name for note in pitch.allowed_pitches),
            pitch.minimum.name if pitch.minimum else "",
            pitch.maximum.name if pitch.maximum else "",
            constraint.locked,
        ))
    ranges = tuple((voice.value, profile.voice_ranges[voice].minimum.name,
                    profile.voice_ranges[voice].maximum.name) for voice in VOICE_ORDER)
    return (
        problem.key_tonic, problem.mode, harmony.label,
        tuple(member.name_no_octave for member in harmony.members), harmony.inversion,
        tuple(voices), ranges, profile.id, profile.require_complete_triads,
        profile.allow_incomplete_dominant_seventh, profile.permit_voice_unisons,
        profile.max_tenor_bass_spacing,
        slot.harmony.exact_bass_pitch.name if slot.harmony.exact_bass_pitch else "",
        tuple(slot.harmony.required_chord_tones),
        tuple(slot.harmony.forbidden_chord_tones),
        tuple(slot.harmony.forbidden_harmonies),
        slot.harmony.required_doubling.value if slot.harmony.required_doubling else "",
    )


def _voice_pools(problem: PartWritingProblem, slot_index: int,
                 harmony: NormalizedHarmony, profile: RuleProfile) -> dict[Voice, list[Note]]:
    slot = problem.slots[slot_index]
    pools: dict[Voice, list[Note]] = {}
    bass_member = harmony.members[harmony.inversion]
    for voice in VOICE_ORDER:
        allowed_range = profile.voice_ranges[voice]
        members = (bass_member,) if voice == Voice.BASS else harmony.members
        pool = []
        for member in members:
            for note in _note_pool(member, allowed_range.minimum.midi,
                                   allowed_range.maximum.midi):
                if _matches_early(note, slot.voice(voice), harmony, problem):
                    pool.append(note)
        if voice == Voice.BASS and slot.harmony.exact_bass_pitch is not None:
            exact = slot.harmony.exact_bass_pitch
            pool = [note for note in pool if note == exact]
        pools[voice] = sorted(set(pool), key=lambda note: (note.midi, note.diatonic_index,
                                                           note.name_no_octave))
    return pools


def enumerate_voicings(problem: PartWritingProblem, slot_index: int,
                       harmony: NormalizedHarmony, profile: RuleProfile,
                       *, maximum: int = 2000) -> list[CandidateVoicing]:
    key = _constraint_signature(problem, slot_index, harmony, profile)
    cached = _CACHE.get(key)
    if cached is not None:
        return list(cached[:maximum])
    pools = _voice_pools(problem, slot_index, harmony, profile)
    if any(not pools[voice] for voice in VOICE_ORDER):
        _CACHE[key] = ()
        return []
    candidates = []
    for notes in product(*(pools[voice] for voice in VOICE_ORDER)):
        voicing = Voicing(*notes)
        # Cheapest vertical checks before building full diagnostics.
        if not (voicing.soprano.midi >= voicing.alto.midi
                >= voicing.tenor.midi >= voicing.bass.midi):
            continue
        if voicing.soprano.midi - voicing.alto.midi > 12:
            continue
        if voicing.alto.midi - voicing.tenor.midi > 12:
            continue
        if voicing.tenor.midi - voicing.bass.midi > profile.max_tenor_bass_spacing:
            continue
        evaluation = validate_local(slot_index, problem, voicing, harmony, profile)
        if evaluation.hard_violations:
            continue
        candidates.append(CandidateVoicing(
            voicing, evaluation.soft_score,
            tuple(sorted(evaluation.score_breakdown.items())),
        ))
    candidates.sort(key=lambda item: (round(item.local_score, 8),
                                      item.voicing.spelled_tuple,
                                      item.voicing.midi_tuple))
    if len(_CACHE) >= _CACHE_MAX:
        _CACHE.pop(next(iter(_CACHE)))
    _CACHE[key] = tuple(candidates)
    return candidates[:maximum]


def factor_count(voicing: Voicing, harmony: NormalizedHarmony,
                 factor: ChordFactor) -> int:
    return sum(harmony.factor_for(note) == factor for note in voicing.notes)
