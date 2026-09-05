import random
import pytest
from music_theory.theory.pitch import Note
from music_theory.theory.jazz import ii_v_i, shell_voicings
from music_theory.exercises.registry import generate


def test_spelled_progressions_and_shared_guides():
    normal = ii_v_i(Note.parse("C4"))
    assert [[n.name_no_octave for n in c.notes] for c in normal] == [
        ["D", "F", "A", "C"], ["G", "B", "D", "F"], ["C", "E", "G", "B"]]
    sub = ii_v_i(Note.parse("C4"), substitute=True)
    assert [n.name_no_octave for n in sub[1].notes] == ["Db", "F", "Ab", "Cb"]
    assert {n.pc for n in normal[1].guides} == {n.pc for n in sub[1].guides}
    assert [n.name_no_octave for n in ii_v_i(Note.parse("C4"), minor=True)[0].notes] == ["D", "F", "Ab", "C"]
    for source, voiced in zip(normal, shell_voicings(normal)):
        assert {n.pc for n in voiced} == {source.notes[0].pc, *(n.pc for n in source.guides)}


@pytest.mark.parametrize("etype", ["jazz_ii_v_i", "jazz_guide_tones", "jazz_tritone_sub", "jazz_progression_ear", "play_jazz_shell"])
def test_jazz_generators_across_difficulties(etype):
    for level in range(11):
        ex = generate(etype, level, random.Random(level))
        assert ex.grade(ex.answer) and ex.explanation
