"""Application bootstrap and shared context."""

from __future__ import annotations

import sys
from dataclasses import dataclass

from . import __app_name__, __version__


@dataclass
class AppContext:
    settings: object
    db: object
    engine: object
    curriculum: object
    scheduler: object
    midi: object = None


def build_context() -> AppContext:
    from .storage import Database, Settings
    from .audio import AudioEngine
    from .curriculum import CURRICULUM
    from .adaptive import Scheduler

    settings = Settings()
    db = Database()
    engine = AudioEngine(settings)
    scheduler = Scheduler(db, CURRICULUM)
    scheduler.ensure_bootstrap()
    ctx = AppContext(settings=settings, db=db, engine=engine,
                     curriculum=CURRICULUM, scheduler=scheduler)
    return ctx


def main() -> int:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QIcon

    from .ui.theme import apply_theme
    from .ui.main_window import MainWindow
    from .paths import resources_dir
    from .errors import install_excepthook

    install_excepthook()
    app = QApplication(sys.argv)
    app.setApplicationName(__app_name__)
    app.setApplicationVersion(__version__)
    apply_theme(app)

    icon_path = resources_dir() / "icons" / "icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    ctx = build_context()

    # Optional MIDI keyboard
    try:
        from .audio.midi_input import MidiInput
        ctx.midi = MidiInput()
        name = ctx.settings.get("midi_input", "")
        if name:
            ctx.midi.start(name)
    except Exception:  # noqa: BLE001 - MIDI is optional
        ctx.midi = None

    window = MainWindow(ctx)
    window.show()
    rc = app.exec()
    try:
        ctx.engine.close()
        if ctx.midi:
            ctx.midi.stop()
        ctx.db.close()
    except Exception:  # noqa: BLE001
        pass
    return rc
