"""Generate README demo media (PNG + GIF) by driving the real app offscreen.

Runs the actual MainWindow on the offscreen Qt platform with a throwaway
profile in a temp APPDATA, walks the main flows (dashboard, lessons, drills,
dictation, placement, piano, stats), grabs frames, and assembles animated
GIFs into docs/media/. Build-time tool only - never shipped.

Usage:
    python build\\make_demo_media.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# Must happen before any music_theory import so all state lands in temp.
# NOTE: uses the real "windows" QPA (offscreen has no fonts on Windows) but
# the window is created with WA_DontShowOnScreen, so nothing ever appears.
_TMP = tempfile.mkdtemp(prefix="mtm_demo_")
os.environ["APPDATA"] = _TMP

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
MEDIA = ROOT / "docs" / "media"
FRAMES = Path(_TMP) / "frames"
MEDIA.mkdir(parents=True, exist_ok=True)
FRAMES.mkdir(parents=True, exist_ok=True)

GIF_WIDTH = 960
WINDOW_SIZE = (1140, 840)


def main() -> int:
    from PyQt6.QtWidgets import QApplication

    from music_theory.app import AppContext
    from music_theory.ui.theme import apply_theme

    app = QApplication([])
    apply_theme(app)

    from music_theory.storage import Database, Settings
    from music_theory.audio import AudioEngine
    from music_theory.curriculum import CURRICULUM
    from music_theory.adaptive import Scheduler

    settings = Settings()
    settings.set("audio_backend", "synth")   # keep the demo run light
    settings.set("master_volume", 0.0)
    settings.set("placement_done", True)
    db = Database()
    engine = AudioEngine(settings)
    scheduler = Scheduler(db, CURRICULUM)
    scheduler.ensure_bootstrap()
    ctx = AppContext(settings=settings, db=db, engine=engine,
                     curriculum=CURRICULUM, scheduler=scheduler)

    _seed_demo_data(ctx)

    from PyQt6.QtCore import Qt
    from music_theory.ui.main_window import MainWindow
    win = MainWindow(ctx)
    win.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    win.resize(*WINDOW_SIZE)
    win.show()
    _pump(app)

    shots: dict[str, list[tuple[str, int]]] = {}

    def grab(gif: str, name: str, duration_ms: int) -> None:
        _pump(app)
        path = FRAMES / f"{gif}_{len(shots.get(gif, [])):02d}_{name}.png"
        win.grab().save(str(path))
        shots.setdefault(gif, []).append((str(path), duration_ms))
        print(f"  frame {path.name}")

    _capture_tour(app, win, grab)
    _capture_lesson(app, win, grab)
    _capture_drill(app, win, ctx, grab)
    _capture_staff(app, win, ctx, grab)
    _capture_dictation(app, win, ctx, grab)
    _capture_fifths(app, win, grab)
    _capture_themes(app, win, ctx, grab)
    _capture_celebration(app, win, grab)
    _capture_placement(app, win, grab)

    for gif, frames in shots.items():
        _assemble(gif, frames)

    _theme_strip(app, win, ctx)

    # hero screenshot: the dashboard, full resolution
    win.go_to("dashboard")
    _pump(app)
    win.grab().save(str(MEDIA / "screenshot-dashboard.png"))
    print("wrote screenshot-dashboard.png")

    win.close()
    engine.close()
    db.close()
    return 0


def _pump(app, n: int = 6) -> None:
    for _ in range(n):
        app.processEvents()


def _seed_demo_data(ctx) -> None:
    """Make the dashboard/stats look lived-in: a week-long streak, XP, and
    mixed mastery across the first skills of each domain."""
    import datetime
    import random

    ctx.db.update_profile(name="Alex", streak_days=7,
                          last_active_day=datetime.date.today().isoformat())
    rng = random.Random(7)
    skills = [s for s in ctx.curriculum if s.schedulable][:14]
    for i, skill in enumerate(skills):
        n = max(3, 14 - i)
        for k in range(n):
            correct = rng.random() < (0.92 - 0.04 * i)
            ctx.scheduler.record(skill.id, correct, difficulty=min(9.0, 1.0 + i * 0.5),
                                 domain=skill.domain, etype=skill.etypes[0],
                                 response_ms=2500, source="course")
        ctx.db.kv_set(f"taught.{skill.id}", True)
    ctx.db.add_xp(38)  # today's progress toward the daily goal
    from music_theory.achievements import evaluate_lesson
    evaluate_lesson(ctx.db, accuracy=92, lesson_len=10)


def _capture_tour(app, win, grab) -> None:
    print("tour.gif")
    win.go_to("dashboard"); grab("tour", "dashboard", 2000)
    win.go_to("practice"); grab("tour", "practice", 1700)
    win.go_to("piano")
    piano_screen = win.screens["piano"]
    for m in (60, 64, 67):
        piano_screen.piano._press(m)
    grab("tour", "piano", 1700)
    for m in (60, 64, 67):
        piano_screen.piano._release(m)
    win.go_to("reference"); grab("tour", "reference", 1700)
    win.go_to("stats"); grab("tour", "stats", 1700)
    win.go_to("achievements"); grab("tour", "awards", 1700)
    win.go_to("settings"); grab("tour", "settings", 1700)


def _capture_lesson(app, win, grab) -> None:
    """First-time skill: mini-lesson pages, then straight into the drill."""
    print("lesson.gif")
    ctx = win.ctx
    # un-teach everything so whichever skill the session picks shows its lesson
    for skill in ctx.curriculum:
        if skill.schedulable:
            ctx.db.kv_set(f"taught.{skill.id}", "")
    win.go_to("session")
    session = win.screens["session"]
    pages = 0
    while session.lesson.isVisible() and pages < 3:
        grab("lesson", f"page{pages + 1}", 2300)
        session.lesson._next()
        _pump(app)
        pages += 1
    # whatever follows the lesson (the first drill) is the payoff frame
    grab("lesson", "drill", 2600)


def _capture_drill(app, win, ctx, grab) -> None:
    """A multiple-choice drill: question, correct answer, wrong answer."""
    print("drill.gif")
    from music_theory.exercises.base import InputMode
    from music_theory.exercises.registry import types_for_domain, safe_generate
    import random

    rng = random.Random(3)
    practice = win.screens["practice"]
    etype = None
    for cand in types_for_domain("theory"):
        ex = safe_generate(cand, 2.0, rng)
        if ex.input_mode == InputMode.MULTIPLE_CHOICE and 3 <= len(ex.choices) <= 6:
            etype = cand
            break
    if etype is None:
        return
    win.go_to("practice")
    _pump(app)
    practice.preset(etype=etype)
    _pump(app)
    player = practice.player
    grab("drill", "question", 2300)
    answer = str(player.ex.answer)
    right = next((b for b in player._choice_btns
                  if b.property("choiceValue") == answer), None)
    if right is not None:
        right.click()
        grab("drill", "correct", 2600)
    # one more question, answered wrong, to show the teaching feedback
    practice._new()
    _pump(app)
    answer = str(player.ex.answer)
    wrong = next((b for b in player._choice_btns
                  if b.property("choiceValue") != answer), None)
    grab("drill", "question2", 2000)
    if wrong is not None:
        wrong.click()
        grab("drill", "teaching", 3200)


def _capture_dictation(app, win, ctx, grab) -> None:
    """Melodic dictation: listen, enter notes on the piano, see the reveal."""
    print("dictation.gif")
    win.go_to("dictation")
    _pump(app)
    practice = win.screens["practice"]
    player = practice.player
    ex = player.ex
    if ex is None or not isinstance(ex.answer, (list, tuple)):
        return
    grab("dictation", "listen", 2200)
    target = [int(m) for m in ex.answer]
    while len(player._entry) < len(target):
        player._add_entry_note(target[len(player._entry)])
        _pump(app)
        if len(player._entry) in (max(1, len(target) // 2), len(target)):
            grab("dictation", f"enter{len(player._entry)}", 1500)
    player._grade(list(player._entry))
    grab("dictation", "result", 3000)


def _capture_staff(app, win, ctx, grab) -> None:
    """The engraved staff: clean accidentals, then a construction exercise."""
    print("staff.gif")
    practice = win.screens["practice"]
    win.go_to("practice")
    _pump(app)
    practice.preset(domain="theory", etype="note_identification")
    _pump(app)
    grab("staff", "note_id", 2400)
    practice.preset(domain="theory", etype="interval_construction")
    _pump(app)
    player = practice.player
    grab("staff", "build_question", 2400)
    target = [int(m) for m in player.ex.answer]
    for m in target:
        player._add_entry_note(m)
        _pump(app)
    grab("staff", "entered", 1800)
    player._grade(list(player._entry))
    _pump(app)
    grab("staff", "reveal", 3000)


def _capture_fifths(app, win, grab) -> None:
    """The circle-of-fifths reference tool."""
    print("fifths.gif")
    win.go_to("reference")
    _pump(app)
    ref = win.screens["reference"]
    grab("fifths", "c_major", 2200)
    for idx in (1, 3, 10):       # G, A, Bb
        ref.circle.selected = idx
        ref._on_key_picked(idx)
        ref.circle.update()
        _pump(app)
        grab("fifths", f"key{idx}", 1900)
    ref._play_key_scale()
    _pump(app)
    grab("fifths", "scale", 2400)


def _capture_themes(app, win, ctx, grab) -> None:
    """Live theme switching from the Appearance settings."""
    print("themes.gif")
    win.go_to("settings")
    _pump(app)
    settings_screen = win.screens["settings"]
    for theme_name in ("dark", "light", "sepia", "high_contrast"):
        idx = settings_screen.theme_combo.findData(theme_name)
        settings_screen.theme_combo.setCurrentIndex(idx)
        _pump(app, 10)
        grab("themes", theme_name, 2100)
    settings_screen.theme_combo.setCurrentIndex(
        settings_screen.theme_combo.findData("dark"))
    _pump(app, 10)


def _capture_celebration(app, win, grab) -> None:
    """A level-up celebration overlay mid-burst."""
    print("celebration.gif")
    win.go_to("dashboard")
    _pump(app)
    win.celebrate("Theory: Intermediate",
                  "Roman numerals aren't homework anymore. You're reading "
                  "harmony the way a conductor scans a score.")
    _pump(app)
    overlay = win._celebration
    for i, ticks in enumerate((3, 8, 14)):
        for _ in range(ticks):
            overlay._tick()
        _pump(app)
        grab("celebration", f"burst{i}", 700 if i < 2 else 2800)
    overlay.dismiss()
    _pump(app)


def _theme_strip(app, win, ctx) -> None:
    """Side-by-side dashboard in dark / light / high-contrast for the README."""
    from PIL import Image
    from music_theory.ui.theme import apply_theme
    panels = []
    for name in ("dark", "light", "high_contrast"):
        ctx.settings.set("theme", name)
        apply_theme(app, ctx.settings)
        win.go_to("dashboard")
        _pump(app, 10)
        path = FRAMES / f"theme_{name}.png"
        win.grab().save(str(path))
        panels.append(Image.open(path).convert("RGB"))
    ctx.settings.set("theme", "dark")
    apply_theme(app, ctx.settings)
    _pump(app, 6)
    h = min(im.height for im in panels)
    scaled = [im.resize((int(im.width * h / im.height), h), Image.LANCZOS) for im in panels]
    strip = Image.new("RGB", (sum(im.width for im in scaled) + 16 * 2, h), "#000000")
    x = 0
    for im in scaled:
        strip.paste(im, (x, 0))
        x += im.width + 16
    out = MEDIA / "screenshot-themes.png"
    target_w = 1800
    if strip.width > target_w:
        strip = strip.resize((target_w, int(strip.height * target_w / strip.width)),
                             Image.LANCZOS)
    strip.save(out)
    print(f"wrote {out.name}")


def _capture_placement(app, win, grab) -> None:
    print("placement.gif")
    win.go_to("placement")
    _pump(app)
    placement = win.screens["placement"]
    grab("placement", "intro", 2400)
    placement._start()
    _pump(app)
    grab("placement", "question", 2400)
    player = placement.player
    if getattr(player, "_choice_btns", None):
        player._choice_btns[0].click()
        grab("placement", "recorded", 2000)


def _assemble(name: str, frames: list[tuple[str, int]]) -> None:
    from PIL import Image

    images = []
    durations = []
    for path, dur in frames:
        im = Image.open(path).convert("RGB")
        if im.width > GIF_WIDTH:
            im = im.resize((GIF_WIDTH, int(im.height * GIF_WIDTH / im.width)),
                           Image.LANCZOS)
        images.append(im.quantize(colors=256, dither=Image.Dither.NONE))
        durations.append(dur)
    if not images:
        return
    out = MEDIA / f"{name}.gif"
    images[0].save(out, save_all=True, append_images=images[1:],
                   duration=durations, loop=0, optimize=True)
    print(f"wrote {out.name} ({out.stat().st_size // 1024} KB, {len(images)} frames)")


if __name__ == "__main__":
    raise SystemExit(main())
