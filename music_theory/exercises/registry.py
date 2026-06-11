"""Generator registry.

A generator is a callable ``(difficulty: float, rng: random.Random) -> Exercise``
registered under a type id and a domain."""

from __future__ import annotations

import random
from typing import Callable, Optional

from .base import Exercise

GeneratorFn = Callable[[float, random.Random], Exercise]

_REGISTRY: dict[str, GeneratorFn] = {}
_DOMAINS: dict[str, str] = {}
_TITLES: dict[str, str] = {}


def register(etype: str, domain: str, title: str = "") -> Callable[[GeneratorFn], GeneratorFn]:
    def deco(fn: GeneratorFn) -> GeneratorFn:
        _REGISTRY[etype] = fn
        _DOMAINS[etype] = domain
        _TITLES[etype] = title or etype.replace("_", " ").title()
        return fn
    return deco


def get_generator(etype: str) -> Optional[GeneratorFn]:
    return _REGISTRY.get(etype)


def generate(etype: str, difficulty: float = 1.0, rng: Optional[random.Random] = None) -> Exercise:
    fn = _REGISTRY.get(etype)
    if fn is None:
        raise KeyError(f"no generator registered for {etype!r}")
    return fn(difficulty, rng or random.Random())


def _fallback_exercise(difficulty: float) -> Exercise:
    """A trivially valid exercise used only if every generation attempt fails,
    so the UI always has something to show rather than dead-ending."""
    from .base import InputMode
    return Exercise(
        skill_id="fund.note_names", domain="theory", etype="note_identification",
        prompt="Which note is the tonic of C major?",
        input_mode=InputMode.MULTIPLE_CHOICE, answer="C",
        choices=["C", "D", "G", "A"], explanation="C major's tonic is C.",
        difficulty=max(0.0, difficulty),
    )


def safe_generate(etype: str, difficulty: float = 1.0,
                  rng: Optional[random.Random] = None, *, attempts: int = 4) -> Exercise:
    """Generate an exercise, never raising. On failure, retry at progressively
    lower difficulty with a fresh seed, then fall back to a guaranteed item."""
    rng = rng or random.Random()
    last_exc: Optional[Exception] = None
    for i in range(max(1, attempts)):
        diff = max(0.0, difficulty - 0.75 * i)
        try:
            return generate(etype, diff, random.Random(rng.random()))
        except Exception as exc:  # noqa: BLE001 - resilience is the whole point
            last_exc = exc
    try:
        from ..errors import log_exception
        log_exception(f"safe_generate failed for {etype!r} @ {difficulty}: {last_exc!r}")
    except Exception:  # noqa: BLE001
        pass
    return _fallback_exercise(difficulty)


def all_types() -> list[str]:
    return sorted(_REGISTRY)


def types_for_domain(domain: str) -> list[str]:
    return sorted(t for t, d in _DOMAINS.items() if d == domain)


def domain_of(etype: str) -> str:
    return _DOMAINS.get(etype, "")


def title_of(etype: str) -> str:
    return _TITLES.get(etype, etype)
