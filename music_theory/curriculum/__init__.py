"""The curriculum: a prerequisite-gated skill tree spanning absolute beginner
to PhD-level topics, mapping each skill to the generators and difficulty band
that train it."""

from .model import Skill, Curriculum, CURRICULUM, LEVEL_ORDER

__all__ = ["Skill", "Curriculum", "CURRICULUM", "LEVEL_ORDER"]
