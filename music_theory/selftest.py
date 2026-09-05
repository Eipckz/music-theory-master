"""Silent, isolated frozen-app smoke test used before publishing a release."""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import traceback


def run_self_test(report_path: str) -> int:
    report = Path(report_path).resolve()
    report.parent.mkdir(parents=True, exist_ok=True)
    result = {"ok": False, "checks": []}
    ctx = None
    try:
        with tempfile.TemporaryDirectory(prefix="mtm_selftest_") as profile:
            os.environ["APPDATA"] = profile
            os.environ["QT_QPA_PLATFORM"] = "offscreen"
            from PyQt6.QtWidgets import QApplication
            from . import __version__
            from .storage import Settings
            from .app import build_context
            from .ui.main_window import MainWindow
            from .ui.theme import apply_theme
            from .theory.part_writing.models import HarmonyConstraint, HarmonySlot, PartWritingProblem, SolveStatus
            from .theory.part_writing.solver import solve
            from .theory.part_writing.export import export_musicxml
            result["version"] = __version__
            app = QApplication.instance() or QApplication([])
            Settings().set("audio_backend", "synth")
            ctx = build_context()
            apply_theme(app, ctx.settings)
            window = MainWindow(ctx)
            window.show()
            for name in ("part_writing", "reference", "piano", "session"):
                window.go_to(name)
                app.processEvents()
            result["checks"].append("Qt startup and main screens")
            p = PartWritingProblem(slots=[HarmonySlot(HarmonyConstraint(chord_symbol="C9"))])
            solved = solve(p)
            if solved.status != SolveStatus.SOLVED:
                raise RuntimeError(solved.message)
            result["checks"].append("Bundled music21 chord symbols and SATB solver")
            export_musicxml(Path(profile) / "smoke.musicxml", p, solved.solutions[0])
            result["checks"].append("MusicXML export")
            from .audio.synth import _render_note
            samples = _render_note(60, 0.1, 96, 44100)
            if len(samples) == 0:
                raise RuntimeError("Silent synth produced no samples")
            result["checks"].append("Offline synthesizer")
            window.close()
            ctx.engine.close()
            ctx.db.close()
            ctx = None
            result["ok"] = True
    except Exception:
        result["error"] = traceback.format_exc()
    finally:
        if ctx is not None:
            ctx.engine.close()
            ctx.db.close()
        report.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return 0 if result["ok"] else 1
