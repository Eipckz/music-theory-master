"""Render StaffWidget samples to PNGs for visual tuning of the engraving.

Usage: python build/render_staff_preview.py [outdir]
Uses the real "windows" QPA with WA_DontShowOnScreen (the offscreen platform
has no font database on Windows, so music glyphs would render as boxes).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PyQt6.QtCore import Qt  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

from music_theory.theory.pitch import Note  # noqa: E402
from music_theory.ui.widgets.staff import STYLE, StaffWidget  # noqa: E402


def shot(widget: StaffWidget, path: Path, w: int = 700, h: int | None = None) -> None:
    widget.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    widget.resize(w, h or widget.minimumSizeHint().height())
    widget.show()
    pix = widget.grab()
    pix.save(str(path))
    print(f"wrote {path} ({pix.width()}x{pix.height()})")


def main() -> None:
    outdir = Path(sys.argv[1] if len(sys.argv) > 1 else "build/staff_preview")
    outdir.mkdir(parents=True, exist_ok=True)
    _app = QApplication.instance() or QApplication([])

    # 1. accidentals: every glyph next to noteheads, including the old
    #    flat-on-top failure case (Bb4 above the middle line)
    s = StaffWidget("treble")
    s.set_notes([Note("B", -1, 4), Note("F", 1, 5), Note("E", 0, 4),
                 Note("A", -2, 4), Note("C", 2, 5), Note("G", 0, 4)])
    shot(s, outdir / "accidentals.png")

    # 2. adjacent steps legibility: the "is that an A or a B" case
    s2 = StaffWidget("treble")
    s2.set_notes([Note("A", 0, 4), Note("B", 0, 4), Note("C", 0, 5),
                  Note("D", 0, 5), Note("E", 0, 5)])
    shot(s2, outdir / "adjacent_steps.png")

    # 3. key signatures
    s3 = StaffWidget("treble")
    s3.set_key_signature({"kind": "sharp", "count": 4})
    s3.set_notes([Note("E", 0, 4), Note("G", 1, 4), Note("B", 0, 4)])
    shot(s3, outdir / "key_sig_sharps.png")
    s3.set_key_signature({"kind": "flat", "count": 5})
    shot(s3, outdir / "key_sig_flats.png")

    # 4. grand staff with ledger lines (middle C from both sides)
    s4 = StaffWidget("grand")
    s4.set_notes([Note("C", 0, 4), Note("A", 0, 3), Note("E", 0, 5),
                  Note("C", 0, 6), Note("E", 0, 2)])
    shot(s4, outdir / "grand_ledger.png")

    # 5. labels + ghost answer overlay
    STYLE["labels"] = "letters_octave"
    s5 = StaffWidget("treble")
    s5.set_notes([Note("A", 0, 4), Note("C", 1, 5)], ghost=[Note("A", 0, 4), Note("B", 0, 4)])
    shot(s5, outdir / "labels_ghost.png")
    STYLE["labels"] = "off"

    # 6. notehead styles
    for style in ("filled", "outlined", "high_contrast"):
        STYLE["notehead"] = style
        sw = StaffWidget("treble")
        sw.set_notes([Note("F", 0, 4), Note("A", 0, 4), Note("C", 0, 5)])
        shot(sw, outdir / f"style_{style}.png")
    STYLE["notehead"] = "filled"

    # 8. chords: accidental lanes, seconds, durations, meter + barlines
    s8 = StaffWidget("treble")
    s8.set_meter(4, 4)
    s8.set_columns([
        [Note("C", 0, 4), Note("E", -1, 4), Note("G", 0, 4)],          # whole chord
        [Note("D", 0, 4), Note("E", 0, 4), Note("B", -1, 4)],          # second cluster
        [Note("F", 1, 4), Note("A", 0, 4), Note("C", 1, 5), Note("E", 0, 5)],
        [Note("G", 0, 4)],
    ], durations=[4.0, 4.0, 2.0, 2.0])
    shot(s8, outdir / "chords_meter.png")

    # 9. one whole-note chord alone in 4/4 (stacked whole notes, no stem)
    s9 = StaffWidget("treble")
    s9.set_meter(4, 4)
    s9.set_columns([[Note("E", 0, 4), Note("G", 1, 4), Note("B", 0, 4), Note("E", 0, 5)]],
                   durations=[4.0])
    shot(s9, outdir / "whole_chord.png")

    # 7. compact size + highlight off (the minimal look)
    STYLE["line_spacing"] = 12
    STYLE["line_highlight"] = False
    s7 = StaffWidget("treble")
    s7.set_notes([Note("B", -1, 4), Note("A", 0, 4)])
    shot(s7, outdir / "compact_plain.png")
    STYLE["line_spacing"] = 17
    STYLE["line_highlight"] = True


if __name__ == "__main__":
    main()
