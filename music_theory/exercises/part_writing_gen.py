"""Curriculum drills backed by the Four-Part Writing Lab solver."""

from __future__ import annotations

import random

from ..theory.part_writing.generator import PracticeType, generate_practice
from ..theory.part_writing.models import Voice
from .base import Exercise, InputMode
from .registry import register


@register("part_writing_completion", "theory", "Four-Part Writing")
def part_writing_completion(difficulty: float, rng: random.Random) -> Exercise:
    practice_type = (PracticeType.FILL_INNER_VOICE if difficulty < 4
                     else PracticeType.FILL_BOTH_INNER if difficulty < 7
                     else PracticeType.PARTIAL_SCORE)
    practice = generate_practice(difficulty, rng, practice_type)
    answer = [[voicing[voice].midi for voicing in practice.answer.voicings]
              for voice in (Voice.SOPRANO, Voice.ALTO, Voice.TENOR, Voice.BASS)]
    labels = " - ".join(slot.harmony.roman_numeral or "?" for slot in practice.problem.slots)
    given = []
    for voice in (Voice.SOPRANO, Voice.ALTO, Voice.TENOR, Voice.BASS):
        first = practice.problem.slots[0].voice(voice).pitch.exact
        given.append(first.midi if first is not None else answer[list(Voice).index(voice)][0])
    return Exercise(
        skill_id="harmony.part_writing", domain="theory", etype="part_writing_completion",
        prompt=f"In {practice.problem.key_tonic} {practice.problem.mode}, realize {labels}. "
               f"{practice.instructions}",
        input_mode=InputMode.MULTI_VOICE, answer=answer,
        explanation="A valid answer preserves the locks and has zero hard-rule violations.",
        difficulty=difficulty,
        play={"mode": "harmonic", "chords": [list(voicing.midi_tuple)
                                                for voicing in practice.answer.voicings],
              "tempo": practice.problem.tempo},
        tags={"voice_names": ["Soprano", "Alto", "Tenor", "Bass"],
              "given_first_each": given, "match": "exact",
              "part_writing_seed": practice.seed},
    )
