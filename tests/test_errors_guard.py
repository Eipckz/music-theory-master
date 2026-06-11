"""The @guard decorator must (1) swallow exceptions without crashing, and
(2) drop surplus positional args a Qt signal would pass to a slot that does not
declare them (the bug that broke Replay/Next/Continue/Play buttons), while still
forwarding args to slots that do declare them."""

from __future__ import annotations

import music_theory.errors as errors
from music_theory.errors import guard


def _capture():
    msgs = []
    errors.set_notifier(lambda title, message: msgs.append((title, message)))
    return msgs


def teardown_function(_):
    errors.set_notifier(None)


def test_guard_drops_surplus_positional_args():
    msgs = _capture()

    class Slot:
        def __init__(self):
            self.ran = 0

        @guard("slot.no_arg")
        def no_arg(self):
            self.ran += 1

    s = Slot()
    s.no_arg(True)          # Qt 'checked' bool, as clicked() would deliver
    s.no_arg(False, 1, 2)   # extra args are tolerated, not forwarded
    assert s.ran == 2
    assert msgs == []       # no "Action interrupted" toast


def test_guard_preserves_declared_args():
    seen = []

    class Slot:
        @guard("slot.with_value")
        def with_value(self, value):
            seen.append(value)

    Slot().with_value(7)
    Slot().with_value(7, 99)  # surplus beyond 'value' is dropped
    assert seen == [7, 7]


def test_guard_swallows_exceptions_and_notifies():
    msgs = _capture()

    @guard("boom")
    def boom():
        raise RuntimeError("nope")

    assert boom() is None
    assert len(msgs) == 1
    assert msgs[0][0] == "Action interrupted"
