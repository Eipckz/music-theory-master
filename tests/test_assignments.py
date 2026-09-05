import pytest

from music_theory.exercises.assignments import (
    ASSIGNMENT_TYPES, create_assignment, save_json, load_assignment, make_result,
    check_result, assignment_id,
)


@pytest.mark.parametrize("etype", ASSIGNMENT_TYPES)
def test_assignment_exchange_and_regrading(etype, tmp_path):
    for difficulty in (0, 5, 10):
        assignment = create_assignment("Test practice", [etype], difficulty, 2, 19)
        file = tmp_path / "practice.json"
        save_json(file, assignment)
        loaded, exercises = load_assignment(file)
        answers = [e.answer for e in exercises]
        result = make_result(loaded, "Learner", answers)
        result["correct"] = 0
        assert check_result(loaded, result)["correct"] == 2


def test_corruption_and_mismatched_results(tmp_path):
    a = create_assignment("A", ["modal_degree"], 4, 1, 0)
    b = create_assignment("B", ["modal_degree"], 4, 1, 0)
    with pytest.raises(ValueError):
        check_result(b, make_result(a, "Name", [a["items"][0]["answer"]]))
    a["items"][0]["play"] = {"mode": "melody", "midis": [60], "tempo": 0}
    a["id"] = assignment_id(a)
    path = tmp_path / "bad.json"
    save_json(path, a)
    with pytest.raises(ValueError):
        load_assignment(path)
