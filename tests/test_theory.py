"""Theory correctness, cross-validated against music21 where it is the
academic source of truth."""

from __future__ import annotations

import random

import pytest

from music_theory.theory.pitch import Note, interval_between, transpose
from music_theory.theory.chords import (
    triad, seventh, roman_to_chord, chord_to_roman, _diatonic_roman_to_chord,
)
from music_theory.theory.scales import scale_notes, key_signature
from music_theory.theory.settheory import normal_form, prime_form, interval_vector, forte_name


def test_interval_basic():
    iv = interval_between(Note("C", 0, 4), Note("G", 0, 4))
    assert iv.number == 5 and iv.quality == "P"


def test_transpose_spelling():
    n = transpose(Note("C", 0, 4), 3, "M")  # major third
    assert (n.letter, n.alter) == ("E", 0)


def test_triad_members():
    c = triad(Note("C", 0, 4), "major")
    assert [m.pc for m in c.members] == [0, 4, 7]
    d = triad(Note("D", 0, 4), "minor")
    assert [m.pc for m in d.members] == [2, 5, 9]


def test_seventh_members():
    g7 = seventh(Note("G", 0, 3), "dom7")
    assert sorted(m.pc for m in g7.members) == [2, 5, 7, 11]


def test_scale_major_spelling():
    notes = scale_notes(Note("D", 0, 4), "major")
    assert [n.name_no_octave for n in notes] == ["D", "E", "F#", "G", "A", "B", "C#"]


def test_key_signature_counts():
    assert key_signature(Note("G", 0, 4), "major")["count"] == 1
    assert key_signature(Note("F", 0, 4), "major")["kind"] == "flat"


def test_set_theory_known_values():
    assert tuple(prime_form([0, 4, 7])) == (0, 3, 7)
    assert interval_vector([0, 4, 7]) == [0, 0, 1, 1, 1, 0]
    # music21 distinguishes Z/A/B variants; the triad belongs to class 3-11
    assert forte_name((0, 3, 7)).startswith("3-11")


@pytest.mark.parametrize("seed", range(8))
def test_prime_form_matches_music21(seed):
    m21 = pytest.importorskip("music21")
    rng = random.Random(seed)
    pcs = sorted(rng.sample(range(12), rng.randint(3, 6)))
    ours = tuple(prime_form(pcs))
    ref = tuple(m21.chord.Chord(pcs).primeForm)
    assert ours == ref


@pytest.mark.parametrize("figure,pcs", [("I", {0, 4, 7}), ("ii", {2, 5, 9}),
                                        ("V", {7, 11, 2}), ("vi", {9, 0, 4})])
def test_roman_to_chord_pcs(figure, pcs):
    ch = roman_to_chord(figure, "C", "major")
    assert {m.pc for m in ch.members} == pcs


def test_chord_to_roman_dominant():
    ch = triad(Note("G", 0, 4), "major")
    rn = chord_to_roman(ch.members, "C", "major")
    assert "V" in rn


# All keys (including remote ones) x figures must never raise: this is the
# exact path that crashed Learn mode (e.g. Gb / C# with a V65 figure).
_ALL_KEYS = ["C", "G", "D", "A", "E", "B", "F#", "C#", "F", "Bb", "Eb", "Ab", "Db", "Gb", "Cb"]
_FIGURES = ["I", "ii", "iii", "IV", "V", "vi", "vii\u00b0", "V7", "V65", "ii6",
            "V/V", "V/vi", "i", "ii\u00b0", "III", "iv", "VI"]


@pytest.mark.parametrize("key", _ALL_KEYS)
def test_roman_to_chord_never_raises_in_any_key(key):
    for mode in ("major", "minor"):
        for fig in _FIGURES:
            ch = roman_to_chord(fig, key, mode)
            assert ch.members
            for n in ch.members:
                assert -2 <= n.alter <= 2  # never an illegal accidental


@pytest.mark.parametrize("key", ["C", "G", "D", "F", "Bb", "Eb", "A", "E"])
def test_diatonic_fallback_matches_music21(key):
    """The music21-free fallback must agree on pitch content for the figures the
    app actually generates, so a trimmed build stays correct."""
    figs_major = ["I", "ii", "iii", "IV", "V", "vi", "vii\u00b0", "V7", "ii6", "V65", "I64"]
    figs_minor = ["i", "ii\u00b0", "III", "iv", "V", "VI", "vii\u00b0", "V7"]
    for mode, figs in (("major", figs_major), ("minor", figs_minor)):
        for fig in figs:
            ref = roman_to_chord(fig, key, mode)            # music21 path
            alt = _diatonic_roman_to_chord(fig, key, mode)  # pure python
            assert {m.pc for m in ref.members} == {m.pc for m in alt.members}, (key, mode, fig)
