"""About screen."""

from __future__ import annotations

from PyQt6.QtWidgets import QVBoxLayout, QWidget

from ... import __app_name__, __version__
from ..common import card, heading, subtle


class AboutScreen(QWidget):
    def __init__(self, ctx, parent=None) -> None:
        super().__init__(parent)
        self.ctx = ctx
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 20)
        root.setSpacing(14)
        root.addWidget(heading(__app_name__))
        frame, lay = card(f"Version {__version__}")
        lay.addWidget(subtle(
            "An offline, adaptive trainer for music theory, aural skills, and piano - "
            "from absolute beginner to graduate level. Exercises are generated endlessly "
            "and tuned to your mastery, with melodic dictation built in from the start."))
        lay.addWidget(subtle(
            "Audio uses a bundled SoundFont via FluidSynth when available, with a built-in "
            "synthesizer fallback. All progress is stored locally on your computer; the app "
            "makes no network connections."))
        lay.addWidget(subtle(
            "Built with PyQt6, music21, NumPy, and SciPy."))
        root.addWidget(frame)
        root.addStretch(1)
