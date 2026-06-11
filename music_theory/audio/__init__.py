"""Audio subsystem: realistic SoundFont synthesis (fluidsynth) with an
always-available numpy synth fallback, plus live MIDI keyboard input."""

from .engine import AudioEngine, Note
from .events import melody_events, chord_events, sequence_events

__all__ = ["AudioEngine", "Note", "melody_events", "chord_events", "sequence_events"]
