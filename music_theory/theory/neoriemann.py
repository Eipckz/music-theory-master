"""Neo-Riemannian transformations (P, L, R and compositions) on consonant
triads, represented as (root pitch-class, is_major)."""

from __future__ import annotations

from typing import Iterable

from .pitch import Note

Triad = tuple[int, bool]  # (root pc, is_major)


def P(t: Triad) -> Triad:
    root, is_major = t
    return (root, not is_major)


def L(t: Triad) -> Triad:
    root, is_major = t
    return ((root + 4) % 12, False) if is_major else ((root + 8) % 12, True)


def R(t: Triad) -> Triad:
    root, is_major = t
    return ((root + 9) % 12, False) if is_major else ((root + 3) % 12, True)


PLR = {"P": P, "L": L, "R": R}


def nr_transform(t: Triad, ops: Iterable[str]) -> Triad:
    """Apply a sequence of single-letter transforms left to right."""
    cur = t
    for op in ops:
        cur = PLR[op](cur)
    return cur


def triad_pcs(t: Triad) -> list[int]:
    root, is_major = t
    third = (root + (4 if is_major else 3)) % 12
    fifth = (root + 7) % 12
    return [root, third, fifth]


def triad_name(t: Triad) -> str:
    root, is_major = t
    name = Note.from_midi(60 + root, prefer_sharps=True).name_no_octave
    return f"{name}{'' if is_major else 'm'}"


def parse_triad(name: str) -> Triad:
    name = name.strip()
    is_major = not name.endswith("m")
    base = name[:-1] if name.endswith("m") else name
    return (Note.parse(base + "4").pc, is_major)
