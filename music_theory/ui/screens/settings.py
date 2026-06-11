"""Settings screen: appearance (theme, accent, scale, staff engraving),
audio backend/device, soundfont, MIDI input, instrument, volume, tempo,
and profile name.

Appearance changes apply and persist immediately (live preview); audio and
profile changes apply on the "Apply settings" button as before.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QScrollArea, QSlider, QSpinBox, QVBoxLayout, QWidget,
)

from ...errors import guard
from ...theory.pitch import Note
from .. import theme
from ..common import card, heading, subtle
from ..widgets import StaffWidget
from ..widgets.staff import configure_staff_appearance

_BACKENDS = [("Automatic (best available)", "auto"),
             ("SoundFont (FluidSynth)", "fluidsynth"),
             ("Built-in synth", "synth")]
_INSTRUMENTS = [("Acoustic Grand Piano", 0), ("Electric Piano", 4), ("Harpsichord", 6),
                ("Vibraphone", 11), ("Church Organ", 19), ("Nylon Guitar", 24),
                ("Violin", 40), ("Cello", 42), ("Trumpet", 56), ("Flute", 73)]

_STAFF_SIZES = [("Compact", "compact"), ("Comfortable (recommended)", "comfortable"),
                ("Large", "large")]
_NOTEHEADS = [("Filled (engraved)", "filled"), ("Outlined", "outlined"),
              ("High contrast", "high_contrast")]
_NOTE_LABELS = [("Off", "off"), ("Letters", "letters"),
                ("Letters + octave", "letters_octave")]
_PAPERS = [("Theme default", ""), ("Ivory", "#f6f3ea"), ("White", "#ffffff"),
           ("Soft gray", "#eceef2")]
_UI_SCALES = [("Auto (match system)", 0.0), ("90%", 0.9), ("100%", 1.0),
              ("110%", 1.1), ("125%", 1.25), ("150%", 1.5), ("175%", 1.75),
              ("200%", 2.0)]

# The recommended out-of-box appearance (the "Reset" target).
_APPEARANCE_DEFAULTS = {
    "theme": "dark", "accent_color": "", "ui_scale": 0.0, "reduce_motion": False,
    "staff_size": "comfortable", "staff_accidental_size": 1.0,
    "staff_accidental_gap": 1.0, "staff_notehead_style": "filled",
    "staff_note_labels": "off", "staff_line_highlight": True, "staff_paper": "",
}


class SettingsScreen(QWidget):
    def __init__(self, ctx, parent=None) -> None:
        super().__init__(parent)
        self.ctx = ctx
        self._loading = True
        s = self.ctx.settings

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        scroll.setWidget(content)
        outer.addWidget(scroll)

        root = QVBoxLayout(content)
        root.setContentsMargins(28, 24, 28, 20)
        root.setSpacing(14)
        root.addWidget(heading("Settings"))

        prof_card, pc = card("Profile")
        form = QFormLayout()
        self.name_edit = QLineEdit(self.ctx.db.get_profile().get("name", "Learner"))
        form.addRow("Name", self.name_edit)
        pc.addLayout(form)
        root.addWidget(prof_card)

        root.addWidget(self._build_appearance_card())

        audio_card, ac = card("Audio")
        af = QFormLayout()
        self.backend_combo = QComboBox()
        for label, val in _BACKENDS:
            self.backend_combo.addItem(label, val)
        self._select_data(self.backend_combo, s.get("audio_backend", "auto"))
        af.addRow("Sound engine", self.backend_combo)

        sf_row = QHBoxLayout()
        self.sf_edit = QLineEdit(s.get("soundfont", ""))
        self.sf_edit.setPlaceholderText("(bundled SoundFont)")
        browse = QPushButton("Browse")
        browse.setObjectName("Secondary")
        browse.clicked.connect(self._browse_sf)
        sf_row.addWidget(self.sf_edit, 1)
        sf_row.addWidget(browse)
        af.addRow("SoundFont", sf_row)

        self.instr_combo = QComboBox()
        for label, prog in _INSTRUMENTS:
            self.instr_combo.addItem(label, prog)
        self._select_data(self.instr_combo, s.get("instrument_program", 0))
        af.addRow("Instrument", self.instr_combo)

        self.device_combo = QComboBox()
        self.device_combo.addItem("System default", -1)
        for idx, name in self._output_devices():
            self.device_combo.addItem(name, idx)
        self._select_data(self.device_combo, s.get("audio_device", -1))
        af.addRow("Output device", self.device_combo)

        self.vol = QSlider(Qt.Orientation.Horizontal)
        self.vol.setAccessibleName("Master volume")
        self.vol.setRange(0, 100)
        self.vol.setValue(int(s.get("master_volume", 0.8) * 100))
        af.addRow("Volume", self.vol)

        self.tempo = QSpinBox()
        self.tempo.setAccessibleName("Default tempo")
        self.tempo.setToolTip("Playback speed for listening exercises (90 = normal). "
                              "You can also change speed next to the Play button.")
        self.tempo.setRange(40, 220)
        self.tempo.setValue(int(s.get("default_tempo", 90)))
        af.addRow("Default tempo", self.tempo)

        self.status = subtle("")
        ac.addLayout(af)
        ac.addWidget(self.status)
        root.addWidget(audio_card)

        midi_card, mc = card("MIDI keyboard")
        mf = QFormLayout()
        self.midi_combo = QComboBox()
        self.midi_combo.addItem("None", "")
        if self.ctx.midi is not None:
            for name in self.ctx.midi.list_devices():
                self.midi_combo.addItem(name, name)
        self._select_data(self.midi_combo, s.get("midi_input", ""))
        mf.addRow("Input", self.midi_combo)
        self.note_names = QCheckBox("Show note names on the keyboard")
        self.note_names.setChecked(bool(s.get("show_note_names", True)))
        mf.addRow("", self.note_names)
        mc.addLayout(mf)
        root.addWidget(midi_card)

        save = QPushButton("Apply settings")
        save.clicked.connect(self._apply)
        root.addWidget(save, alignment=Qt.AlignmentFlag.AlignLeft)

        danger_card, dc = card("Progress")
        dc.addWidget(subtle("Reset all learning progress: mastery, XP, streak, "
                            "achievements, and placement. This cannot be undone."))
        reset_btn = QPushButton("Reset progress…")
        reset_btn.setObjectName("Danger")
        reset_btn.clicked.connect(self._reset_progress)
        dc.addWidget(reset_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        root.addWidget(danger_card)

        root.addStretch(1)
        self._loading = False
        self._refresh_status()

    # -- appearance ---------------------------------------------------------
    def _build_appearance_card(self) -> QWidget:
        s = self.ctx.settings
        app_card, lay = card("Appearance")
        lay.addWidget(subtle("Changes apply immediately and are remembered."))
        form = QFormLayout()

        self.theme_combo = QComboBox()
        self.theme_combo.setAccessibleName("Color theme")
        for label, val in theme.THEME_LABELS:
            self.theme_combo.addItem(label, val)
        self._select_data(self.theme_combo, s.get("theme", "dark"))
        self.theme_combo.currentIndexChanged.connect(self._apply_appearance)
        form.addRow("Theme", self.theme_combo)

        self.accent_combo = QComboBox()
        self.accent_combo.setAccessibleName("Accent color")
        for label, val in theme.ACCENT_PRESETS:
            self.accent_combo.addItem(label, val)
        self._select_data(self.accent_combo, s.get("accent_color", ""))
        self.accent_combo.currentIndexChanged.connect(self._apply_appearance)
        form.addRow("Accent color", self.accent_combo)

        self.scale_combo = QComboBox()
        self.scale_combo.setAccessibleName("Interface scale")
        for label, val in _UI_SCALES:
            self.scale_combo.addItem(label, val)
        self._select_data(self.scale_combo, float(s.get("ui_scale", 0.0)))
        self.scale_combo.currentIndexChanged.connect(self._apply_appearance)
        form.addRow("Interface scale", self.scale_combo)

        self.reduce_motion = QCheckBox("Reduce motion (skip celebration animations)")
        self.reduce_motion.setChecked(bool(s.get("reduce_motion", False)))
        self.reduce_motion.toggled.connect(self._apply_appearance)
        form.addRow("", self.reduce_motion)
        lay.addLayout(form)

        lay.addWidget(QLabel("<b>Staff &amp; notation</b>"))
        sform = QFormLayout()

        self.staff_size_combo = QComboBox()
        self.staff_size_combo.setAccessibleName("Staff size")
        for label, val in _STAFF_SIZES:
            self.staff_size_combo.addItem(label, val)
        self._select_data(self.staff_size_combo, s.get("staff_size", "comfortable"))
        self.staff_size_combo.currentIndexChanged.connect(self._apply_appearance)
        sform.addRow("Staff size", self.staff_size_combo)

        self.notehead_combo = QComboBox()
        self.notehead_combo.setAccessibleName("Notehead style")
        for label, val in _NOTEHEADS:
            self.notehead_combo.addItem(label, val)
        self._select_data(self.notehead_combo, s.get("staff_notehead_style", "filled"))
        self.notehead_combo.currentIndexChanged.connect(self._apply_appearance)
        sform.addRow("Noteheads", self.notehead_combo)

        self.labels_combo = QComboBox()
        self.labels_combo.setAccessibleName("Note name labels on the staff")
        for label, val in _NOTE_LABELS:
            self.labels_combo.addItem(label, val)
        self._select_data(self.labels_combo, s.get("staff_note_labels", "off"))
        self.labels_combo.currentIndexChanged.connect(self._apply_appearance)
        sform.addRow("Note names", self.labels_combo)

        self.paper_combo = QComboBox()
        self.paper_combo.setAccessibleName("Staff paper color")
        for label, val in _PAPERS:
            self.paper_combo.addItem(label, val)
        self._select_data(self.paper_combo, s.get("staff_paper", ""))
        self.paper_combo.currentIndexChanged.connect(self._apply_appearance)
        sform.addRow("Paper color", self.paper_combo)

        self.acc_size = QSlider(Qt.Orientation.Horizontal)
        self.acc_size.setAccessibleName("Accidental size")
        self.acc_size.setRange(70, 160)
        self.acc_size.setValue(int(float(s.get("staff_accidental_size", 1.0)) * 100))
        self.acc_size.valueChanged.connect(self._apply_appearance)
        sform.addRow("Accidental size", self.acc_size)

        self.acc_gap = QSlider(Qt.Orientation.Horizontal)
        self.acc_gap.setAccessibleName("Accidental spacing")
        self.acc_gap.setRange(50, 200)
        self.acc_gap.setValue(int(float(s.get("staff_accidental_gap", 1.0)) * 100))
        self.acc_gap.valueChanged.connect(self._apply_appearance)
        sform.addRow("Accidental gap", self.acc_gap)

        self.line_highlight = QCheckBox("Highlight the line or space under each note")
        self.line_highlight.setChecked(bool(s.get("staff_line_highlight", True)))
        self.line_highlight.toggled.connect(self._apply_appearance)
        sform.addRow("", self.line_highlight)
        lay.addLayout(sform)

        # live preview: B-flat next to the head was the original bug, keep it
        # front and center so any spacing tweak is judged on the hard case
        self.staff_preview = StaffWidget("treble")
        self.staff_preview.set_key_signature({"kind": "sharp", "count": 2})
        self.staff_preview.set_notes([
            Note("A", 0, 4), Note("B", -1, 4), Note("C", 1, 5), Note("E", 0, 4),
        ])
        lay.addWidget(self.staff_preview)

        reset = QPushButton("Reset to recommended defaults")
        reset.setObjectName("Secondary")
        reset.clicked.connect(self._reset_appearance)
        lay.addWidget(reset, alignment=Qt.AlignmentFlag.AlignLeft)
        return app_card

    @guard("Settings._apply_appearance")
    def _apply_appearance(self, *_args) -> None:
        if self._loading:
            return
        s = self.ctx.settings
        s.set("theme", self.theme_combo.currentData())
        s.set("accent_color", self.accent_combo.currentData())
        s.set("ui_scale", float(self.scale_combo.currentData()))
        s.set("reduce_motion", self.reduce_motion.isChecked())
        s.set("staff_size", self.staff_size_combo.currentData())
        s.set("staff_notehead_style", self.notehead_combo.currentData())
        s.set("staff_note_labels", self.labels_combo.currentData())
        s.set("staff_paper", self.paper_combo.currentData())
        s.set("staff_accidental_size", self.acc_size.value() / 100.0)
        s.set("staff_accidental_gap", self.acc_gap.value() / 100.0)
        s.set("staff_line_highlight", self.line_highlight.isChecked())
        self._restyle()

    @guard("Settings._reset_appearance")
    def _reset_appearance(self) -> None:
        s = self.ctx.settings
        for key, value in _APPEARANCE_DEFAULTS.items():
            s.set(key, value)
        self._loading = True
        try:
            self._select_data(self.theme_combo, "dark")
            self._select_data(self.accent_combo, "")
            self._select_data(self.scale_combo, 0.0)
            self.reduce_motion.setChecked(False)
            self._select_data(self.staff_size_combo, "comfortable")
            self._select_data(self.notehead_combo, "filled")
            self._select_data(self.labels_combo, "off")
            self._select_data(self.paper_combo, "")
            self.acc_size.setValue(100)
            self.acc_gap.setValue(100)
            self.line_highlight.setChecked(True)
        finally:
            self._loading = False
        self._restyle()

    def _restyle(self) -> None:
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is not None:
            theme.apply_theme(app, self.ctx.settings)
        configure_staff_appearance(self.ctx.settings)
        self.staff_preview.updateGeometry()
        self.staff_preview.update()

    # -- progress -----------------------------------------------------------
    @guard("Settings._reset_progress")
    def _reset_progress(self) -> None:
        confirm = QMessageBox.question(
            self, "Reset progress",
            "This permanently erases all mastery, XP, streak, achievements, and "
            "placement results. Are you sure?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self.ctx.db.reset_progress()
        self.ctx.settings.set("placement_done", False)
        self.ctx.scheduler.ensure_bootstrap()
        win = self.window()
        if hasattr(win, "toast"):
            win.toast("Progress reset. Starting fresh!", kind="info")

    def on_show(self) -> None:
        self._refresh_status()

    # -- helpers ----------------------------------------------------------
    def _select_data(self, combo: QComboBox, data) -> None:
        idx = combo.findData(data)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def _output_devices(self):
        try:
            import sounddevice as sd
            out = []
            for i, dev in enumerate(sd.query_devices()):
                if dev.get("max_output_channels", 0) > 0:
                    out.append((i, f"{i}: {dev['name']}"))
            return out
        except Exception:  # noqa: BLE001
            return []

    def _browse_sf(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select SoundFont", "",
                                              "SoundFont (*.sf2 *.sf3);;All files (*)")
        if path:
            self.sf_edit.setText(path)

    def _refresh_status(self) -> None:
        eng = self.ctx.engine
        msg = f"Active engine: <b>{eng.backend_name}</b>"
        if eng.backend_error and eng.backend_name == "synth":
            msg += f"  ·  SoundFont unavailable ({eng.backend_error})"
        self.status.setText(msg)

    @guard("Settings._apply")
    def _apply(self) -> None:
        s = self.ctx.settings
        name = self.name_edit.text().strip() or "Learner"
        self.ctx.db.update_profile(name=name)
        s.set("name", name)
        s.set("audio_backend", self.backend_combo.currentData())
        s.set("soundfont", self.sf_edit.text().strip())
        s.set("instrument_program", int(self.instr_combo.currentData()))
        s.set("audio_device", int(self.device_combo.currentData()))
        s.set("master_volume", self.vol.value() / 100.0)
        s.set("default_tempo", int(self.tempo.value()))
        s.set("show_note_names", self.note_names.isChecked())
        midi_name = self.midi_combo.currentData()
        s.set("midi_input", midi_name)

        self.ctx.engine.reload_backend()
        if self.ctx.midi is not None:
            if midi_name:
                self.ctx.midi.start(midi_name)
            else:
                self.ctx.midi.stop()
        self._refresh_status()
