"""Self-contained music-theory engine.

Fast, deterministic, fully unit-tested primitives for spelled pitches,
intervals, scales, keys, chords, roman numerals, pitch-class set theory,
twelve-tone rows, and Neo-Riemannian transforms. music21 is used in the test
suite to cross-validate outputs and (optionally) for MusicXML/MIDI I/O."""

from .pitch import (
    Note,
    Interval,
    interval_between,
    transpose,
    midi_to_name,
    name_to_midi,
    LETTERS,
)
from .scales import Scale, SCALE_TYPES, scale_notes, key_signature, KEYS
from .chords import (
    Chord,
    triad,
    seventh,
    CHORD_QUALITIES,
    roman_to_chord,
    chord_to_roman,
    figured_bass,
)
from .settheory import PCSet, normal_form, prime_form, interval_vector, forte_name
from .twelvetone import ToneRow, row_matrix
from .neoriemann import nr_transform, PLR

__all__ = [
    "Note", "Interval", "interval_between", "transpose", "midi_to_name",
    "name_to_midi", "LETTERS", "Scale", "SCALE_TYPES", "scale_notes",
    "key_signature", "KEYS", "Chord", "triad", "seventh", "CHORD_QUALITIES",
    "roman_to_chord", "chord_to_roman", "figured_bass", "PCSet", "normal_form",
    "prime_form", "interval_vector", "forte_name", "ToneRow", "row_matrix",
    "nr_transform", "PLR",
]
