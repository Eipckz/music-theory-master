"""Graduate / PhD-level post-tonal exercise generators: pitch-class set theory,
twelve-tone rows and matrices, and Neo-Riemannian transformations."""

from __future__ import annotations

import random
import re

from ..theory.settheory import (
    PCSet, normal_form, prime_form, interval_vector, forte_name,
)
from ..theory.twelvetone import ToneRow, pc_label
from ..theory.neoriemann import nr_transform, triad_name, parse_triad
from .base import Exercise, InputMode
from .registry import register
from . import _util as U

_PC_TOKENS = {"t": 10, "a": 10, "e": 11, "b": 11}


def parse_pcs(text, mod: bool = True) -> list[int]:
    """Parse a list of pitch classes from free text (handles digits, T/E)."""
    if isinstance(text, (list, tuple)):
        return [int(x) % 12 if mod else int(x) for x in text]
    tokens = re.findall(r"10|11|[0-9tTeEaAbB]", str(text))
    out = []
    for tok in tokens:
        low = tok.lower()
        val = _PC_TOKENS.get(low, None)
        val = int(tok) if val is None else val
        out.append(val % 12 if mod else val)
    return out


def _fmt(pcs) -> str:
    return " ".join(pc_label(p) for p in pcs)


def _ordered_checker(expected):
    def chk(response, _answer):
        return parse_pcs(response) == list(expected)
    return chk


def _set_checker(expected):
    exp = {int(x) % 12 for x in expected}
    def chk(response, _answer):
        return {x % 12 for x in parse_pcs(response)} == exp
    return chk


def _vector_checker(expected):
    def chk(response, _answer):
        nums = [int(x) for x in re.findall(r"\d", str(response))] if not isinstance(response, (list, tuple)) \
            else [int(x) for x in response]
        return nums == list(expected)
    return chk


def _random_set(rng: random.Random, k: int) -> list[int]:
    return sorted(rng.sample(range(12), k))


@register("pcset_normal_form", "theory", "PC-Set: Normal Form")
def pcset_normal_form(difficulty: float, rng: random.Random) -> Exercise:
    k = 3 if difficulty < 3 else rng.randint(3, 5)
    pcs = _random_set(rng, k)
    nf = normal_form(pcs)
    return Exercise(
        skill_id="posttonal.normal_form", domain="theory", etype="pcset_normal_form",
        prompt=f"Give the NORMAL FORM of the set {{{_fmt(pcs)}}} (use T=10, E=11).",
        input_mode=InputMode.TEXT, answer=_fmt(nf),
        explanation=f"Normal form: [{_fmt(nf)}]", difficulty=difficulty,
        checker=_ordered_checker(nf),
    )


@register("pcset_prime_form", "theory", "PC-Set: Prime Form")
def pcset_prime_form(difficulty: float, rng: random.Random) -> Exercise:
    k = 3 if difficulty < 3 else rng.randint(3, 6)
    pcs = _random_set(rng, k)
    pf = prime_form(pcs)
    return Exercise(
        skill_id="posttonal.prime_form", domain="theory", etype="pcset_prime_form",
        prompt=f"Give the PRIME FORM of the set {{{_fmt(pcs)}}}.",
        input_mode=InputMode.TEXT, answer=_fmt(pf),
        explanation=f"Prime form: ({_fmt(pf)}), Forte {forte_name(tuple(pf))}",
        difficulty=difficulty, checker=_ordered_checker(pf),
    )


@register("pcset_interval_vector", "theory", "PC-Set: Interval Vector")
def pcset_interval_vector(difficulty: float, rng: random.Random) -> Exercise:
    k = rng.randint(3, 5)
    pcs = _random_set(rng, k)
    iv = interval_vector(pcs)
    return Exercise(
        skill_id="posttonal.interval_vector", domain="theory", etype="pcset_interval_vector",
        prompt=f"Give the interval-class VECTOR of {{{_fmt(pcs)}}} (six numbers).",
        input_mode=InputMode.TEXT, answer="".join(str(x) for x in iv),
        explanation=f"Interval vector: <{' '.join(str(x) for x in iv)}>",
        difficulty=difficulty, checker=_vector_checker(iv),
    )


@register("forte_identification", "theory", "PC-Set: Forte Name")
def forte_identification(difficulty: float, rng: random.Random) -> Exercise:
    k = 3 if difficulty < 4 else rng.randint(3, 5)
    pcs = _random_set(rng, k)
    pf = prime_form(pcs)
    answer = forte_name(tuple(pf))
    distractors = set()
    while len(distractors) < 6:
        other = prime_form(_random_set(rng, k))
        nm = forte_name(tuple(other))
        if nm != answer:
            distractors.add(nm)
    return Exercise(
        skill_id="posttonal.forte", domain="theory", etype="forte_identification",
        prompt=f"What is the Forte set-class name of {{{_fmt(pcs)}}}?",
        input_mode=InputMode.MULTIPLE_CHOICE, answer=answer,
        choices=U.choices_from(answer, list(distractors), rng, k=4),
        explanation=f"Prime form ({_fmt(pf)}) = Forte {answer}.", difficulty=difficulty,
    )


@register("set_transposition", "theory", "Tn / TnI Transformation")
def set_transposition(difficulty: float, rng: random.Random) -> Exercise:
    k = rng.randint(3, 4)
    s = PCSet.of(_random_set(rng, k))
    n = rng.randint(1, 11)
    invert = difficulty >= 5 and rng.random() < 0.5
    result = s.TnI(n) if invert else s.Tn(n)
    op = f"T{n}I" if invert else f"T{n}"
    expected = sorted(result.pcs)
    return Exercise(
        skill_id="posttonal.transforms", domain="theory", etype="set_transposition",
        prompt=f"Apply {op} to {{{_fmt(sorted(s.pcs))}}}. List the resulting pitch classes.",
        input_mode=InputMode.TEXT, answer=_fmt(expected),
        explanation=f"{op} gives {{{_fmt(expected)}}}.", difficulty=difficulty,
        checker=_set_checker(expected),
    )


def _random_row(rng: random.Random) -> list[int]:
    row = list(range(12))
    rng.shuffle(row)
    return row


@register("row_form_identification", "theory", "12-Tone: Identify Row Form")
def row_form_identification(difficulty: float, rng: random.Random) -> Exercise:
    base = _random_row(rng)
    tr = ToneRow(tuple(base))
    kind = rng.choice(["P", "I", "R", "RI"] if difficulty >= 4 else ["P", "I", "R"])
    n = rng.randint(0, 11)
    seq = tr.form(kind, n)
    label = f"{kind}{n}"
    distractors = []
    for kk in ("P", "I", "R", "RI"):
        for nn in rng.sample(range(12), 3):
            distractors.append(f"{kk}{nn}")
    return Exercise(
        skill_id="posttonal.twelve_tone", domain="theory", etype="row_form_identification",
        prompt=f"The prime row P0 is [{_fmt(tr.p0)}]. Which row form is "
               f"[{_fmt(seq)}]?",
        input_mode=InputMode.MULTIPLE_CHOICE, answer=label,
        choices=U.choices_from(label, distractors, rng, k=4),
        explanation=f"That row form is {label}.", difficulty=difficulty,
    )


@register("row_matrix_lookup", "theory", "12-Tone: Matrix Lookup")
def row_matrix_lookup(difficulty: float, rng: random.Random) -> Exercise:
    base = _random_row(rng)
    tr = ToneRow(tuple(base))
    kind = rng.choice(["P", "I", "R", "RI"])
    n = rng.randint(0, 11)
    seq = tr.form(kind, n)
    return Exercise(
        skill_id="posttonal.twelve_tone", domain="theory", etype="row_matrix_lookup",
        prompt=f"Given P0 = [{_fmt(tr.p0)}], write out {kind}{n} (12 pitch classes, T=10 E=11).",
        input_mode=InputMode.TEXT, answer=_fmt(seq),
        explanation=f"{kind}{n} = [{_fmt(seq)}]", difficulty=difficulty,
        checker=_ordered_checker(seq),
    )


@register("neo_riemannian", "theory", "Neo-Riemannian Transformation")
def neo_riemannian(difficulty: float, rng: random.Random) -> Exercise:
    roots = ["C", "G", "D", "A", "F", "E", "Bb"]
    name = rng.choice(roots) + rng.choice(["", "m"])
    t = parse_triad(name)
    n_ops = 1 if difficulty < 4 else rng.randint(1, 3)
    ops = "".join(rng.choice("PLR") for _ in range(n_ops))
    result = nr_transform(t, ops)
    answer = triad_name(result)
    distractors = [triad_name(((r + i) % 12, b))
                   for r in range(0, 12, 2) for i in (0,) for b in (True, False)]
    return Exercise(
        skill_id="posttonal.neo_riemannian", domain="theory", etype="neo_riemannian",
        prompt=f"Apply the transformation '{ops}' to the {name} triad. Name the result.",
        input_mode=InputMode.MULTIPLE_CHOICE, answer=answer,
        choices=U.choices_from(answer, distractors, rng, k=4),
        explanation=f"{name} --{ops}--> {answer}.", difficulty=difficulty,
    )
