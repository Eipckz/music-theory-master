---
name: add-exercise-type
description: Add a new exercise type (generator) and/or skill to Music Theory Master — covers the registry contract, curriculum wiring, teaching text, lessons, and the tests that must pass. Use when adding drills, ear-training types, or new curriculum skills.
---

# Adding an exercise type / skill

## 1. Write the generator
In `music_theory/exercises/{theory_gen,aural_gen,piano_gen,posttonal_gen}.py`:

```python
@register("my_etype", "aural", "Display Title")
def my_etype(difficulty: float, rng: random.Random) -> Exercise:
    ...
```

Hard contract (parametrized tests enforce it for every registered type):
- Must work and **never raise** for difficulty 0.0–10.0 (scale content by difficulty bands; see `_util.band`, `pick_key_name`).
- `ex.grade(ex.answer)` must be True (the canonical answer self-grades).
- MULTIPLE_CHOICE: answer must be in `choices`, choices unique (`U.choices_from`).
- Use only the provided `rng` for randomness (reproducibility).
- `play=` audio spec modes: melody | interval | chord | sequence | harmonic | note (see `render_play` in `exercises/base.py`).
- Input modes and their answer shapes: MULTIPLE_CHOICE/TEXT → str; NOTE_ENTRY → [midi]; PIANO → set-like [midi]; RHYTHM → [beats]; SEQUENCE → [labels]; MULTI_VOICE → [[midi per voice], ...] top voice first, with tags `voice_names`, `given_first_each`.

## 2. Wire the curriculum (if it's a new skill)
`music_theory/curriculum/model.py` → add a `Skill` with id, domain, level
(Beginner/Early/Intermediate/Advanced/Graduate), `etypes=(...)`, `prereqs`,
and `diff_range` matching where the content is meaningful.

## 3. Teach it (required, not optional)
- `exercises/teaching.py`: `_CONCEPTS["my_etype"]` (shown on wrong answers) and ideally `_HINTS`.
- `curriculum/lessons.py`: `LESSONS["skill.id"]` = 2–5 `_P(...)` pages, with `play=` audio examples where the concept is audible. **`test_lessons.py` fails if a skill has no lesson.**
- Optionally add the etype to a placement ladder in `adaptive/placement.py` (`_DOMAIN_LADDER`) at the right difficulty position.

## 4. Verify
```powershell
python -m pytest tests/test_generators.py tests/test_lessons.py tests/test_adaptive.py -q
python -m pytest tests -q          # full suite before shipping
```
A new generator is picked up by the parametrized tests automatically — no test
boilerplate needed unless the behavior is novel (then add a focused test).
