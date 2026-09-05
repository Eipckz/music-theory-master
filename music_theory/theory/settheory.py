"""Pitch-class set theory: normal form, prime form (Rahn), interval-class
vector, and Tn/TnI. Forte set-class names are resolved via music21."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import re
from typing import Iterable


PC_NAMES_SHARP = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
PC_NAMES_FLAT = ("C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B")


def pc_label(pc: int) -> str:
    """Single-character pitch-class label (T=10, E=11)."""
    value = int(pc) % 12
    return "TE"[value - 10] if value >= 10 else str(value)


def pc_name(pc: int, *, prefer_flats: bool = False) -> str:
    """Human-readable chromatic pitch name for a pitch class."""
    names = PC_NAMES_FLAT if prefer_flats else PC_NAMES_SHARP
    return names[int(pc) % 12]


def pc_from_token(token: str | int) -> int:
    """Parse a numeric/T/E pitch class or an octave-free note name.

    Post-tonal entry deliberately treats enharmonic spellings as equivalent;
    scale-degree and tonal spelling remain separate concepts elsewhere.
    """
    if isinstance(token, int):
        return token % 12
    raw = str(token).strip().replace("♯", "#").replace("♭", "b")
    upper = raw.upper()
    if upper == "T":
        return 10
    if upper == "E" and len(raw) == 1:
        # In a numeric row, E conventionally means eleven. Use an octave-free
        # pitch name in a note-name context through an explicit accidental or
        # the UI note/name toggle; the workbench labels both representations.
        return 11
    if re.fullmatch(r"(?:10|11|[0-9])", raw):
        return int(raw) % 12
    match = re.fullmatch(r"([A-Ga-g])([#b]{0,2})", raw)
    if not match:
        raise ValueError(f"invalid pitch-class token: {token!r}")
    natural = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
    value = natural[match.group(1).upper()]
    for accidental in match.group(2):
        value += 1 if accidental == "#" else -1
    return value % 12


def parse_pitch_classes(text: str | Iterable[int | str], *, unique: bool = True) -> list[int]:
    """Parse ``0..11``/``T E`` or note-name pitch classes.

    Numeric and note-name input may be comma- or space-separated. Order is
    retained; set-oriented callers use the default de-duplication while tone
    rows pass ``unique=False``.
    """
    if isinstance(text, str):
        cleaned = re.sub(r"[\[\]{}()<>;,|]", " ", text)
        tokens = cleaned.split()
    else:
        tokens = list(text)
    numeric = all(re.fullmatch(r"(?:10|11|[0-9]|[TEte])", str(token).strip())
                  for token in tokens)
    if numeric:
        values = [pc_from_token(token) for token in tokens]
    else:
        natural = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
        values = []
        for token in tokens:
            raw = str(token).strip().replace("♯", "#").replace("♭", "b")
            match = re.fullmatch(r"([A-Ga-g])([#b]{0,2})", raw)
            if not match:
                raise ValueError(f"invalid note-name pitch class: {token!r}")
            value = natural[match.group(1).upper()]
            for accidental in match.group(2):
                value += 1 if accidental == "#" else -1
            values.append(value % 12)
    if not unique:
        return values
    return list(dict.fromkeys(values))


def interval_class(a: int, b: int) -> int:
    """Return the shortest chromatic distance, 0..6, between two pcs."""
    distance = (int(b) - int(a)) % 12
    return min(distance, 12 - distance)


def _dedup_sorted(pcs: Iterable[int]) -> list[int]:
    return sorted({p % 12 for p in pcs})


def _rotations(pcs: list[int]) -> list[list[int]]:
    n = len(pcs)
    rots = []
    for i in range(n):
        rot = pcs[i:] + pcs[:i]
        # express as ascending offsets from the first element
        rots.append([(p - rot[0]) % 12 for p in rot])
    return rots


def normal_form(pcs: Iterable[int]) -> list[int]:
    """Most compact (left-packed) ordering, returned as actual pcs.

    Uses music21 as the source of truth (academic standard); falls back to a
    pure implementation if music21 is unavailable."""
    base = _dedup_sorted(pcs)
    if not base:
        return []
    try:
        import music21
        return [int(p) for p in music21.chord.Chord(base).normalOrder]
    except Exception:  # noqa: BLE001
        return _normal_form_pure(base)


def _normal_form_pure(pcs: Iterable[int]) -> list[int]:
    base = _dedup_sorted(pcs)
    if not base:
        return []
    n = len(base)
    candidates = [base[i:] + base[:i] for i in range(n)]

    def span(rot: list[int]) -> int:
        return (rot[-1] - rot[0]) % 12

    best = candidates[0]
    best_key = None
    for rot in candidates:
        # compare span, then successively inner spans for left-packing
        offsets = [(p - rot[0]) % 12 for p in rot]
        key = tuple([span(rot)] + [offsets[-(k)] for k in range(1, n)])
        if best_key is None or key < best_key:
            best_key, best = key, rot
    return best


def transpose_pcs(pcs: Iterable[int], n: int) -> list[int]:
    return sorted({(p + n) % 12 for p in pcs})


def invert_pcs(pcs: Iterable[int], axis: int = 0) -> list[int]:
    return sorted({(axis - p) % 12 for p in pcs})


def prime_form(pcs: Iterable[int]) -> list[int]:
    """Prime form (music21's Forte-compatible algorithm) starting at 0."""
    base = _dedup_sorted(pcs)
    if not base:
        return []
    try:
        import music21
        return [int(p) for p in music21.chord.Chord(base).primeForm]
    except Exception:  # noqa: BLE001
        return _prime_form_pure(base)


def _prime_form_pure(pcs: Iterable[int]) -> list[int]:
    base = _dedup_sorted(pcs)
    if not base:
        return []

    def packed(seq: list[int]) -> list[int]:
        nf = _normal_form_pure(seq)
        return [(p - nf[0]) % 12 for p in nf]

    return min(packed(base), packed(invert_pcs(base)))


def interval_vector(pcs: Iterable[int]) -> list[int]:
    base = _dedup_sorted(pcs)
    vec = [0, 0, 0, 0, 0, 0]
    for i in range(len(base)):
        for j in range(i + 1, len(base)):
            ic = (base[j] - base[i]) % 12
            ic = min(ic, 12 - ic)
            if 1 <= ic <= 6:
                vec[ic - 1] += 1
    return vec


@lru_cache(maxsize=256)
def forte_name(prime: tuple[int, ...]) -> str:
    """Resolve a Forte set-class name via music21; fall back to the prime form."""
    try:
        import music21
        sc = music21.chord.Chord([int(p) for p in prime])
        name = sc.forteClass
        if name and name != "N/A":
            return name
    except Exception:  # noqa: BLE001 - never fail an exercise on lookup
        pass
    return "[" + "".join(pc_label(p) for p in prime) + "]"


@dataclass(frozen=True)
class PCSet:
    pcs: tuple[int, ...]

    @classmethod
    def of(cls, pcs: Iterable[int]) -> "PCSet":
        return cls(tuple(_dedup_sorted(pcs)))

    @property
    def normal_form(self) -> list[int]:
        return normal_form(self.pcs)

    @property
    def prime_form(self) -> list[int]:
        return prime_form(self.pcs)

    @property
    def interval_vector(self) -> list[int]:
        return interval_vector(self.pcs)

    @property
    def forte(self) -> str:
        return forte_name(tuple(self.prime_form))

    def Tn(self, n: int) -> "PCSet":
        return PCSet.of(transpose_pcs(self.pcs, n))

    def TnI(self, n: int) -> "PCSet":
        return PCSet.of([(n - p) % 12 for p in self.pcs])
