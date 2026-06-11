"""Appearance system: palettes, accent derivation, staff style settings."""

from __future__ import annotations

import pytest

from music_theory.storage.settings import _SCHEMA
from music_theory.theory.pitch import Note
from music_theory.ui import theme
from music_theory.ui.widgets.staff import (
    SIZE_PRESETS, STYLE, StaffWidget, configure_staff_appearance,
)


@pytest.fixture
def qapp():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(autouse=True)
def _restore_theme_and_style():
    """Each test leaves the module-level theme/staff state at defaults."""
    yield
    theme.set_palette("dark")
    STYLE.update({"line_spacing": SIZE_PRESETS["comfortable"], "acc_scale": 1.0,
                  "acc_gap": 1.0, "notehead": "filled", "labels": "off",
                  "line_highlight": True, "paper": ""})


# -- palettes ---------------------------------------------------------------

def test_every_palette_defines_full_token_set():
    base = set(theme.PALETTES["dark"])
    for name, pal in theme.PALETTES.items():
        assert set(pal) == base, f"palette {name} is missing/adding tokens"


def test_palette_text_contrast_meets_aa():
    for name, pal in theme.PALETTES.items():
        for surface in ("BG", "SURFACE", "SURFACE_2"):
            ratio = theme.contrast_ratio(pal["TEXT"], pal[surface])
            assert ratio >= 4.5, f"{name}: TEXT on {surface} = {ratio:.2f}"
        assert theme.contrast_ratio(pal["STAFF_INK"], pal["STAFF_PAPER"]) >= 7


def test_set_palette_updates_module_attributes():
    dark_accent = theme.ACCENT
    theme.set_palette("light")
    assert theme.CURRENT_THEME == "light"
    assert theme.ACCENT != dark_accent
    assert theme.STAFF_PAPER == theme.PALETTES["light"]["STAFF_PAPER"]
    theme.set_palette("dark")
    assert theme.ACCENT == dark_accent


def test_set_palette_unknown_falls_back_to_dark():
    theme.set_palette("does-not-exist")
    assert theme.CURRENT_THEME == "dark"


def test_accent_override_derives_hover_pressed_and_text():
    violet = dict(theme.ACCENT_PRESETS)["Violet"]
    theme.set_palette("dark", violet)
    assert theme.TOKENS["ACCENT"] == violet
    assert theme.TOKENS["ACCENT_HOVER"] != violet
    assert theme.TOKENS["ACCENT_PRESSED"] != violet
    # text on the accent fill must meet AA for normal text
    assert theme.contrast_ratio(theme.TOKENS["TEXT_DARK"], violet) >= 4.5


def test_text_on_accent_contrast_for_all_presets_and_palettes():
    for _, accent in theme.ACCENT_PRESETS:
        for pal_name in theme.PALETTES:
            theme.set_palette(pal_name, accent)
            fill = theme.TOKENS["ACCENT"]
            assert theme.contrast_ratio(theme.TOKENS["TEXT_DARK"], fill) >= 4.5, \
                f"{pal_name} + accent {accent or 'default'}"


def test_build_qss_substitutes_every_token(qapp):
    for name in theme.PALETTES:
        theme.set_palette(name)
        qss = theme._build_qss(1.0)
        assert "%" not in qss.replace("%v", "").replace("%m", ""), \
            f"unsubstituted token in {name} QSS"


def test_apply_theme_reads_settings(qapp, settings):
    settings.set("theme", "sepia")
    settings.set("accent_color", "#14a89c")
    theme.apply_theme(qapp, settings)
    assert theme.CURRENT_THEME == "sepia"
    assert theme.TOKENS["ACCENT"] == "#14a89c"
    # malformed accent is ignored, not applied
    settings.set("accent_color", "not-a-color")
    theme.apply_theme(qapp, settings)
    assert theme.TOKENS["ACCENT"] == theme.PALETTES["sepia"]["ACCENT"]


def test_ui_scale_setting_overrides_system(qapp, settings):
    settings.set("ui_scale", 1.5)
    assert theme.compute_scale(qapp, settings) == 1.5
    settings.set("ui_scale", 99.0)   # clamped
    assert theme.compute_scale(qapp, settings) == 2.0
    settings.set("ui_scale", 0.0)    # auto: falls back to system-font factor
    assert 0.9 <= theme.compute_scale(qapp, settings) <= 2.0


# -- settings schema --------------------------------------------------------

def test_appearance_keys_in_schema_with_sane_defaults():
    expected = {
        "theme": "dark", "accent_color": "", "ui_scale": 0.0,
        "reduce_motion": False, "staff_size": "comfortable",
        "staff_accidental_size": 1.0, "staff_accidental_gap": 1.0,
        "staff_notehead_style": "filled", "staff_note_labels": "off",
        "staff_line_highlight": True, "staff_paper": "",
    }
    for key, default in expected.items():
        assert key in _SCHEMA, key
        assert _SCHEMA[key][0] == default, key


def test_appearance_settings_persist(settings):
    settings.set("theme", "light")
    settings.set("staff_size", "large")
    settings.set("staff_note_labels", "letters")
    reloaded = type(settings)(settings.path)
    assert reloaded.get("theme") == "light"
    assert reloaded.get("staff_size") == "large"
    assert reloaded.get("staff_note_labels") == "letters"


# -- staff appearance -------------------------------------------------------

def test_configure_staff_appearance_reads_settings(settings):
    settings.set("staff_size", "large")
    settings.set("staff_accidental_size", 1.2)
    settings.set("staff_notehead_style", "outlined")
    settings.set("staff_note_labels", "letters_octave")
    settings.set("staff_line_highlight", False)
    settings.set("staff_paper", "#ffffff")
    configure_staff_appearance(settings)
    assert STYLE["line_spacing"] == SIZE_PRESETS["large"]
    assert STYLE["acc_scale"] == 1.2
    assert STYLE["notehead"] == "outlined"
    assert STYLE["labels"] == "letters_octave"
    assert STYLE["line_highlight"] is False
    assert STYLE["paper"] == "#ffffff"


def test_configure_staff_appearance_rejects_garbage(settings):
    settings.set("staff_size", "enormous")
    settings.set("staff_notehead_style", "sparkly")
    settings.set("staff_note_labels", "emoji")
    settings.set("staff_paper", "red")          # not #rrggbb
    configure_staff_appearance(settings)
    assert STYLE["line_spacing"] == SIZE_PRESETS["comfortable"]
    assert STYLE["notehead"] == "filled"
    assert STYLE["labels"] == "off"
    assert STYLE["paper"] == ""


def test_staff_widget_follows_style_then_override(qapp):
    w = StaffWidget("treble")
    STYLE["line_spacing"] = 22
    assert w.line_spacing == 22
    w.line_spacing = 12              # explicit instance override wins
    assert w.line_spacing == 12
    STYLE["line_spacing"] = 17
    assert w.line_spacing == 12


def test_staff_minimum_height_scales_with_size(qapp):
    w = StaffWidget("treble")
    STYLE["line_spacing"] = 12
    compact = w.minimumSizeHint().height()
    STYLE["line_spacing"] = 22
    large = w.minimumSizeHint().height()
    assert large > compact
    g = StaffWidget("grand")
    assert g.minimumSizeHint().height() > w.minimumSizeHint().height()


def test_staff_renders_all_styles_without_error(qapp):
    """Render every notehead style/label mode to a pixmap (no exceptions)."""
    notes = [Note("B", -1, 4), Note("F", 1, 5), Note("A", -2, 3), Note("C", 2, 6)]
    for style in ("filled", "outlined", "high_contrast"):
        for labels in ("off", "letters", "letters_octave"):
            for highlight in (True, False):
                STYLE.update({"notehead": style, "labels": labels,
                              "line_highlight": highlight})
                for clef in ("treble", "bass", "grand"):
                    w = StaffWidget(clef)
                    w.resize(640, w.minimumSizeHint().height())
                    w.set_notes(notes, ghost=[Note("C", 0, 4)])
                    w.set_key_signature({"kind": "flat", "count": 5})
                    pix = w.grab()
                    assert not pix.isNull()


def test_settings_screen_appearance_controls_drive_staff_and_theme(qapp):
    """Flip every Appearance control on the real SettingsScreen and assert the
    setting persists and the staff/theme pick it up."""
    from music_theory.app import build_context
    from music_theory.ui.screens.settings import SettingsScreen

    ctx = build_context()
    try:
        screen = SettingsScreen(ctx)
        s = ctx.settings

        def pick(combo, data):
            combo.setCurrentIndex(combo.findData(data))

        pick(screen.theme_combo, "light")
        assert s.get("theme") == "light"
        assert theme.CURRENT_THEME == "light"

        pick(screen.accent_combo, dict(theme.ACCENT_PRESETS)["Teal"])
        assert theme.TOKENS["ACCENT"] == dict(theme.ACCENT_PRESETS)["Teal"]

        pick(screen.scale_combo, 1.5)
        assert s.get("ui_scale") == 1.5

        pick(screen.staff_size_combo, "large")
        assert STYLE["line_spacing"] == SIZE_PRESETS["large"]
        assert screen.staff_preview.line_spacing == SIZE_PRESETS["large"]

        pick(screen.notehead_combo, "high_contrast")
        assert STYLE["notehead"] == "high_contrast"

        pick(screen.labels_combo, "letters")
        assert STYLE["labels"] == "letters"

        pick(screen.paper_combo, "#ffffff")
        assert STYLE["paper"] == "#ffffff"

        screen.acc_size.setValue(130)
        assert STYLE["acc_scale"] == pytest.approx(1.3)

        screen.acc_gap.setValue(150)
        assert STYLE["acc_gap"] == pytest.approx(1.5)

        screen.line_highlight.setChecked(False)
        assert STYLE["line_highlight"] is False

        screen.reduce_motion.setChecked(True)
        assert s.get("reduce_motion") is True

        # one click back to the recommended out-of-box look
        screen._reset_appearance()
        assert s.get("theme") == "dark"
        assert s.get("staff_size") == "comfortable"
        assert STYLE["line_spacing"] == SIZE_PRESETS["comfortable"]
        assert STYLE["notehead"] == "filled"
        assert STYLE["line_highlight"] is True
        assert theme.CURRENT_THEME == "dark"
    finally:
        ctx.engine.close()
        ctx.db.close()


def test_staff_chord_columns_api(qapp):
    """Part 5: chords stack in one column, with durations and a meter."""
    w = StaffWidget("treble")
    w.set_meter(4, 4)
    w.set_columns([
        [Note("C", 0, 4), Note("E", -1, 4), Note("G", 0, 4)],
        [Note("D", 0, 4), Note("E", 0, 4)],          # a second: offset path
        Note("G", 0, 4),                              # plain note column
    ], durations=[4.0, 2.0, 2.0])
    assert len(w._columns) == 3
    assert len(w.notes) == 6                          # flattened for compat
    assert "C4+Eb4+G4" in w.accessibleDescription()
    w.resize(640, w.minimumSizeHint().height())
    assert not w.grab().isNull()                      # renders without error
    # meter off again
    w.set_meter(None)
    assert w.meter is None


def test_staff_grand_chord_splits_across_staves(qapp):
    w = StaffWidget("grand")
    w.set_columns([[Note("C", 0, 3), Note("E", 0, 3), Note("C", 0, 5)]],
                  durations=[4.0])
    w.resize(640, w.minimumSizeHint().height())
    assert not w.grab().isNull()


def test_staff_set_notes_still_sequential_after_columns(qapp):
    w = StaffWidget("treble")
    w.set_columns([[Note("C", 0, 4), Note("E", 0, 4)]])
    w.set_notes([Note("A", 0, 4), Note("B", 0, 4)])
    assert len(w._columns) == 2
    assert all(len(c) == 1 for c in w._columns)
    w.pop_note()
    assert len(w._columns) == 1


def test_staff_accessible_description_unaffected_by_style(qapp):
    w = StaffWidget("treble")
    STYLE["labels"] = "letters_octave"
    w.set_notes([Note("A", 0, 4), Note("B", -1, 4)])
    assert "A4" in w.accessibleDescription()
    assert "Bb4" in w.accessibleDescription() or "B-4" in w.accessibleDescription() \
        or "B♭4" in w.accessibleDescription()
