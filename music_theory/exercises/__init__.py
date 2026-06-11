"""Procedural exercise generators.

Every exercise type is an *infinite* generator: given a difficulty and an RNG
it returns a fresh, self-consistent :class:`Exercise` whose answer is provably
correct. Importing this package registers all generators."""

from .base import Exercise, InputMode, render_play, normalize_answer
from .registry import (
    register,
    get_generator,
    generate,
    safe_generate,
    all_types,
    types_for_domain,
)

# Import generator modules for their registration side effects.
from . import theory_gen  # noqa: F401,E402
from . import aural_gen   # noqa: F401,E402
from . import piano_gen   # noqa: F401,E402
from . import posttonal_gen  # noqa: F401,E402

__all__ = [
    "Exercise", "InputMode", "render_play", "normalize_answer",
    "register", "get_generator", "generate", "safe_generate",
    "all_types", "types_for_domain",
]
