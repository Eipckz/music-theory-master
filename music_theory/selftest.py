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
        with tempfile.TemporaryDirectory(prefix="mtm_selftest_", ignore_cleanup_errors=True) as profile:
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
            for name in ("part_writing", "reference", "piano", "session", "tools", "placement"):
                window.go_to(name)
                app.processEvents()
            result["checks"].append("Qt startup and main screens")
            from .ui.screens.workbench import Workbench
            note_tool = Workbench(ctx)
            rhythm_tool = Workbench(ctx, rhythm=True)
            if "V7 in C major" not in note_tool.report.toPlainText() or "complete" not in rhythm_tool.report.toPlainText():
                raise RuntimeError("Assignment calculators failed their startup examples")
            note_tool.close()
            rhythm_tool.close()
            result["checks"].append("Note analysis and exact rhythm calculator")
            tools_screen = window.screens["tools"]
            for i in range(tools_screen.tabs.count()):
                tools_screen.tabs.setCurrentIndex(i)
                app.processEvents()
            transpose_tool = tools_screen.tabs.widget(0)
            scale_tool = tools_screen.tabs.widget(1)
            worksheet_tool = tools_screen.tabs.widget(3)
            fret_tool = tools_screen.tabs.widget(4)
            if not (transpose_tool.result and scale_tool.matches and worksheet_tool.items and fret_tool.board):
                raise RuntimeError("New practice tools did not produce startup examples")
            from .theory.practice_tools import export_melody, metronome_events, worksheet_html
            export_melody(Path(profile) / "transpose.musicxml", transpose_tool.result)
            if len(metronome_events(120, "2+3", 3, 2)) != 30:
                raise RuntimeError("Metronome event check failed")
            (Path(profile) / "worksheet.html").write_text(worksheet_html(worksheet_tool.items), encoding="utf-8")
            result["checks"].append("Five practice tools and worksheet/transposition exports")
            from .theory.part_writing.harmony import normalize_constraint
            normalize_constraint(HarmonyConstraint(chord_symbol="C9"), "C", "major")
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
