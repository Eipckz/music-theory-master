"""Spelled ii–V–I vocabulary and guide-tone voicings."""
from dataclasses import dataclass

from .pitch import Note, transpose
from .chords import seventh
from .scales import scale_notes


@dataclass(frozen=True)
class JazzChord:
    label: str
    notes: tuple[Note, ...]

    @property
    def guides(self):
        return self.notes[1], self.notes[3]


def ii_v_i(tonic: Note, *, minor=False, substitute=False) -> list[JazzChord]:
    scale = scale_notes(tonic, "harmonic_minor" if minor else "major")
    second = tuple(seventh(scale[1], "halfdim7" if minor else "min7").members)
    dominant_root = transpose(tonic, 2, "m") if substitute else scale[4]
    dominant = tuple(seventh(dominant_root, "dom7").members)
    home = tuple(seventh(tonic, "min7" if minor else "maj7").members)
    return [JazzChord("iiø7" if minor else "ii7", second),
            JazzChord("♭II7" if substitute else "V7", dominant),
            JazzChord("i7" if minor else "Imaj7", home)]


def shell_voicings(chords: list[JazzChord]) -> list[list[Note]]:
    """Root + third/seventh, with nearby guide tones; not a SATB rule checker."""
    from itertools import product
    previous = None
    result = []
    for chord in chords:
        root = Note(chord.notes[0].letter, chord.notes[0].alter, 2)
        a, b = chord.guides
        candidates = []
        for oa, ob in product((3, 4), repeat=2):
            pair = sorted([Note(a.letter, a.alter, oa), Note(b.letter, b.alter, ob)], key=lambda n: n.midi)
            if pair[-1].midi - pair[0].midi <= 12:
                cost = sum(abs(n.midi - old.midi) for n, old in zip(pair, previous)) if previous else sum(n.midi for n in pair)
                candidates.append((cost, pair))
        pair = min(candidates, key=lambda c: c[0])[1]
        result.append([root] + pair)
        previous = pair
    return result
