"""Settings screen: audio backend/device, soundfont, MIDI input, instrument,
volume, tempo, and profile name."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QSlider, QSpinBox, QVBoxLayout, QWidget,
)

from ...errors import guard
from ..common import card, heading, subtle

_BACKENDS = [("Automatic (best available)", "auto"),
             ("SoundFont (FluidSynth)", "fluidsynth"),
             ("Built-in synth", "synth")]
_INSTRUMENTS = [("Acoustic Grand Piano", 0), ("Electric Piano", 4), ("Harpsichord", 6),
                ("Vibraphone", 11), ("Church Organ", 19), ("Nylon Guitar", 24),
                ("Violin", 40), ("Cello", 42), ("Trumpet", 56), ("Flute", 73)]


class SettingsScreen(QWidget):
    def __init__(self, ctx, parent=None) -> None:
        super().__init__(parent)
        self.ctx = ctx
        s = self.ctx.settings
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 20)
        root.setSpacing(14)
        root.addWidget(heading("Settings"))

        prof_card, pc = card("Profile")
        form = QFormLayout()
        self.name_edit = QLineEdit(self.ctx.db.get_profile().get("name", "Learner"))
        form.addRow("Name", self.name_edit)
        pc.addLayout(form)
        root.addWidget(prof_card)

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
        self.vol.setRange(0, 100)
        self.vol.setValue(int(s.get("master_volume", 0.8) * 100))
        af.addRow("Volume", self.vol)

        self.tempo = QSpinBox()
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
        reset_btn = QPushButton("Reset progress\u2026")
        reset_btn.setObjectName("Secondary")
        reset_btn.clicked.connect(self._reset_progress)
        dc.addWidget(reset_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        root.addWidget(danger_card)

        root.addStretch(1)
        self._refresh_status()

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
            msg += f"  \u00b7  SoundFont unavailable ({eng.backend_error})"
        self.status.setText(msg)

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
