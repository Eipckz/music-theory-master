"""Twelve-tone rows, row forms (P/R/I/RI), and the 12x12 matrix."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence


def _normalize(row: Sequence[int]) -> list[int]:
    """Transpose so the row begins on pitch-class 0 (P0)."""
    start = row[0] % 12
    return [(pc - start) % 12 for pc in row]


@dataclass(frozen=True)
class ToneRow:
    row: tuple[int, ...]

    def __post_init__(self) -> None:
        if sorted(p % 12 for p in self.row) != list(range(12)):
            raise ValueError("a tone row must be a permutation of 0..11")

    @property
    def p0(self) -> list[int]:
        return _normalize(self.row)

    def P(self, n: int) -> list[int]:
        return [(x + n) % 12 for x in self.p0]

    def I(self, n: int) -> list[int]:
        return [(n - x) % 12 for x in self.p0]

    def R(self, n: int) -> list[int]:
        return list(reversed(self.P(n)))

    def RI(self, n: int) -> list[int]:
        return list(reversed(self.I(n)))

    def form(self, kind: str, n: int) -> list[int]:
        return {"P": self.P, "I": self.I, "R": self.R, "RI": self.RI}[kind](n)

    def identify(self, seq: Sequence[int]) -> Optional[str]:
        """Return the label (e.g. 'P3', 'RI7') for a row form, if it matches."""
        seq = [p % 12 for p in seq]
        for kind in ("P", "I", "R", "RI"):
            for n in range(12):
                if self.form(kind, n) == seq:
                    return f"{kind}{n}"
        return None


def row_matrix(row: Sequence[int]) -> list[list[int]]:
    """Standard 12x12 matrix: top row P0 (left->right), left column I0 (top->down)."""
    p0 = _normalize(row)
    i0 = [(-x) % 12 for x in p0]
    return [[(p0[j] + i0[i]) % 12 for j in range(12)] for i in range(12)]


def matrix_labels(row: Sequence[int]) -> dict[str, list[str]]:
    """Row/column transposition labels for displaying the matrix."""
    p0 = _normalize(row)
    i0 = [(-x) % 12 for x in p0]
    left = [f"P{i0[i]}" for i in range(12)]
    right = [f"R{i0[i]}" for i in range(12)]
    top = [f"I{p0[j]}" for j in range(12)]
    bottom = [f"RI{p0[j]}" for j in range(12)]
    return {"left": left, "right": right, "top": top, "bottom": bottom}


def pc_label(pc: int) -> str:
    return ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "T", "E"][pc % 12]
