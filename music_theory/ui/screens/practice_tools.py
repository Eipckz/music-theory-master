"""Five complementary practice tools, each with explicit inputs and exports."""
from pathlib import Path
import time

from PyQt6.QtGui import QColor
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QComboBox, QLineEdit,
    QSpinBox, QPushButton, QLabel, QPlainTextEdit, QTabWidget, QFileDialog,
    QTableWidget, QTableWidgetItem, QAbstractItemView, QListWidget, QTextBrowser, QScrollArea, QFrame,
)

from ...errors import guard
from ...theory.pitch import Note
from ...theory.practice_tools import (
    INSTRUMENTS, TUNINGS, WORKSHEET_TYPES, transpose_notes, instrument_interval,
    export_melody, find_scales, metronome_events, tapped_bpm, fretboard,
    worksheet, worksheet_html, parse_notes,
)
from ...exercises.registry import title_of
from ..common import heading
from .. import theme


def combo(items):
    box = QComboBox()
    box.addItems(items)
    return box


def spin(low, high, value):
    box = QSpinBox()
    box.setRange(low, high)
    box.setValue(value)
    return box


class ToolPage(QWidget):
    def __init__(self, ctx, help_text):
        super().__init__()
        self.ctx = ctx
        self.outer = QVBoxLayout(self)
        self.outer.setContentsMargins(8, 8, 8, 8)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.host = QWidget()
        self.scroll.setWidget(self.host)
        self.outer.addWidget(self.scroll, 1)
        self.layout = QVBoxLayout(self.host)
        label = QLabel(help_text)
        self.help_label = label
        label.setWordWrap(True)
        self.layout.addWidget(label)
        label.setObjectName("Subtle")
        self.form = QGridLayout()
        self.form.setHorizontalSpacing(18)
        self.form.setVerticalSpacing(12)
        self.form.setColumnStretch(0, 1)
        self.form.setColumnStretch(1, 1)
        self.field_count = 0
        self.layout.addLayout(self.form)
        self.buttons = QGridLayout()
        self.button_count = 0
        self.outer.addLayout(self.buttons)
        self.report = QPlainTextEdit()
        self.report.setReadOnly(True)
        self.report.setAccessibleName("Tool results")
        self.report.setMinimumHeight(170)
        self.layout.addWidget(self.report, 1)

    def field(self, title, widget):
        widget.setAccessibleName(title)
        cell = QWidget()
        box = QVBoxLayout(cell)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(5)
        label = QLabel(title)
        label.setObjectName("FieldLabel")
        label.setWordWrap(True)
        box.addWidget(label)
        box.addWidget(widget)
        box.addStretch(1)
        self.form.addWidget(cell, self.field_count // 2, self.field_count % 2)
        self.field_count += 1
        return widget

    def button(self, title, handler):
        button = QPushButton(title)
        button.clicked.connect(handler)
        primary = title in ("Transpose", "Find scales", "Start", "Generate", "Generate sheet", "Build fretboard", "Open MusicXML", "Record", "Build progression", "Create")
        if not primary:
            button.setObjectName("Secondary")
        self.buttons.addWidget(button, self.button_count // 3, self.button_count % 3)
        self.button_count += 1
        return button

    def watch(self, widgets, handler):
        for widget in widgets:
            signal = widget.textChanged if isinstance(widget, QLineEdit) else widget.currentTextChanged if isinstance(widget, QComboBox) else widget.valueChanged
            signal.connect(handler)


class TransposePage(ToolPage):
    def __init__(self, ctx):
        super().__init__(ctx, "Transpose a melody with its spelling intact. Omitted octaves default to 4. "
                         "Instrument presets convert written and concert pitches. Export uses quarter notes; rhythm is not inferred.")
        self.notes = self.field("Notes", QLineEdit("C4 E4 G4"))
        self.size = self.field("Interval", QLineEdit("M2"))
        self.direction = self.field("Direction", combo(["Up", "Down"]))
        self.instrument = self.field("Instrument preset", combo(list(INSTRUMENTS)))
        self.conversion = self.field("Conversion", combo(["Written → concert", "Concert → written"]))
        self.button("Apply instrument preset", self.preset)
        self.button("Transpose", self.calculate)
        self.play_btn = self.button("Hear result", self.play)
        self.save_btn = self.button("Export MusicXML", self.save)
        self.watch([self.notes, self.size, self.direction], self.invalidate)
        self.result = []
        self.calculate()

    def invalidate(self):
        self.result = []
        self.play_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.report.setPlainText("Inputs changed. Transpose again.")

    @guard("Transposition.preset")
    def preset(self):
        size, down = instrument_interval(self.instrument.currentText(), self.conversion.currentIndex() == 0)
        self.size.setText(size)
        self.direction.setCurrentIndex(int(down))
        self.calculate()

    @guard("Transposition.calculate")
    def calculate(self):
        self.invalidate()
        try:
            self.result = transpose_notes(self.notes.text(), self.size.text(), self.direction.currentIndex() == 1)
            self.report.setPlainText("Result: " + " ".join(n.name for n in self.result))
            self.play_btn.setEnabled(True)
            self.save_btn.setEnabled(True)
        except ValueError as exc:
            self.report.setPlainText(str(exc))

    @guard("Transposition.play")
    def play(self):
        if self.result:
            self.ctx.engine.play_melody([n.midi for n in self.result])

    @guard("Transposition.save")
    def save(self):
        if self.result:
            path, _ = QFileDialog.getSaveFileName(self, "Export transposed melody", "transposed.musicxml", "MusicXML (*.musicxml)")
            if path:
                export_melody(Path(path), self.result)


class ScaleFinderPage(ToolPage):
    def __init__(self, ctx):
        super().__init__(ctx, "Find scales containing your pitch classes. A match does not establish a tonic or key. "
                         "Major/Ionian and natural minor/Aeolian are combined; melodic minor is ascending.")
        self.notes = self.field("Known notes", QLineEdit("C D E G A"))
        self.tonic = self.field("Optional tonic", QLineEdit(""))
        self.outside = self.field("Allow outside pitch classes", spin(0, 2, 0))
        self.button("Find scales", self.calculate)
        self.selection = self.field("Candidate to hear", QComboBox())
        self.play_btn = self.button("Hear candidate", self.play)
        self.watch([self.notes, self.tonic, self.outside], self.invalidate)
        self.matches = []
        self.calculate()

    def invalidate(self):
        self.matches = []
        self.selection.clear()
        self.play_btn.setEnabled(False)
        self.report.setPlainText("Inputs changed. Find scales again.")

    @guard("ScaleFinder.calculate")
    def calculate(self):
        self.invalidate()
        try:
            self.matches = find_scales(self.notes.text(), self.tonic.text(), self.outside.value())
            lines = []
            for m in self.matches:
                title = f"{m.tonic} {m.kind.replace('_', ' ')}"
                self.selection.addItem(title)
                outside = " ".join(Note.from_midi(60 + p).name_no_octave for p in m.outside) or "none"
                missing = " ".join(n.name_no_octave for n in m.notes if n.pc in m.missing) or "none"
                lines.append(f"{title}: {' '.join(n.name_no_octave for n in m.notes)}\n  Missing: {missing}; outside: {outside}")
            self.report.setPlainText("\n\n".join(lines) or "No match under these constraints.")
            self.play_btn.setEnabled(bool(self.matches))
        except ValueError as exc:
            self.report.setPlainText(str(exc))

    @guard("ScaleFinder.play")
    def play(self):
        if 0 <= self.selection.currentIndex() < len(self.matches):
            notes = self.matches[self.selection.currentIndex()].notes
            self.ctx.engine.play_melody([n.midi for n in notes] + [notes[0].midi + 12])


class MetronomePage(ToolPage):
    def __init__(self, ctx):
        super().__init__(ctx, "BPM counts your chosen beat, not a denominator: for 6/8 use 2 beats and 3 subdivisions "
                         "at dotted-quarter BPM. For additive 5/8 use 2+3 at eighth-note BPM. Runs stop after the chosen bars (maximum three minutes).")
        self.bpm = self.field("Beats per minute", spin(20, 300, 90))
        self.groups = self.field("Beat groups", QLineEdit("4"))
        self.subdivision = self.field("Subdivisions per beat", spin(1, 4, 1))
        self.bars = self.field("Bars", spin(1, 32, 4))
        self.button("Start", self.start)
        self.button("Stop", self.stop)
        self.button("Tap tempo", self.tap)
        self.button("Reset taps", self.reset_taps)
        self.taps = []
        self.running = False
        self.finish_timer = QTimer(self)
        self.finish_timer.setSingleShot(True)
        self.finish_timer.timeout.connect(self.finished)
        self.watch([self.bpm, self.groups, self.subdivision, self.bars], self.stop)
        self.report.setPlainText("Ready. Tap at least twice; pauses longer than three seconds restart measurement.")

    @guard("Metronome.start")
    def start(self):
        self.stop()
        try:
            events = metronome_events(self.bpm.value(), self.groups.text(), self.subdivision.value(), self.bars.value())
            self.ctx.engine.play_events(events)
            self.running = True
            beats = sum(int(x) for x in self.groups.text().split("+")) * self.bars.value()
            self.finish_timer.start(round(beats * 60000 / self.bpm.value()))
            self.report.setPlainText(f"Playing {self.bars.value()} bars at {self.bpm.value()} BPM. Downbeats and group starts are accented.")
        except ValueError as exc:
            self.report.setPlainText(str(exc))

    @guard("Metronome.stop")
    def stop(self):
        self.finish_timer.stop()
        if self.running:
            self.ctx.engine.stop()
        self.running = False
        self.report.setPlainText("Stopped. Press Start to use the current settings.")

    @guard("Metronome.finished")
    def finished(self):
        self.running = False
        self.report.setPlainText("Practice run finished. Press Start to repeat.")

    @guard("Metronome.tap")
    def tap(self):
        now = time.monotonic()
        if self.taps and now - self.taps[-1] > 3:
            self.taps.clear()
        self.taps = (self.taps + [now])[-9:]
        bpm = tapped_bpm(self.taps)
        if bpm is not None:
            self.bpm.setValue(round(bpm))
        self.report.setPlainText(f"{len(self.taps)} taps; " + (f"{bpm:.1f} BPM" if bpm else "keep tapping within 20–300 BPM."))

    @guard("Metronome.reset")
    def reset_taps(self):
        self.taps = []
        self.report.setPlainText("Tap measurement reset.")

    def hideEvent(self, event):
        self.stop()
        super().hideEvent(event)


class WorksheetPage(ToolPage):
    def __init__(self, ctx):
        super().__init__(ctx, "Select written topics and generate a reproducible practice sheet. Save questions and answer key separately as HTML; "
                         "open the file in a browser to print or save as PDF. This ungraded work does not award XP.")
        self.types = QListWidget()
        self.types.addItems([title_of(t) for t in WORKSHEET_TYPES])
        self.types.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.types.setMaximumHeight(130)
        self.types.item(0).setSelected(True)
        self.field("Topics", self.types)
        self.difficulty = self.field("Difficulty", spin(0, 10, 4))
        self.count = self.field("Questions", spin(1, 50, 10))
        self.seed = self.field("Seed", spin(0, 999999, 1234))
        self.button("Generate sheet", self.calculate)
        self.save_questions = self.button("Save questions", lambda: self.save(False))
        self.save_answers = self.button("Save answer key", lambda: self.save(True))
        self.report.hide()
        self.preview = QTextBrowser()
        self.preview.setStyleSheet("QTextBrowser { background: #ffffff; color: #111111; }")
        self.preview.setAccessibleName("Worksheet preview")
        self.layout.addWidget(self.preview, 1)
        self.items = []
        self.watch([self.difficulty, self.count, self.seed], self.invalidate)
        self.types.itemSelectionChanged.connect(self.invalidate)
        self.calculate()

    def invalidate(self):
        self.items = []
        self.save_questions.setEnabled(False)
        self.save_answers.setEnabled(False)
        self.preview.setPlainText("Inputs changed. Generate a fresh worksheet.")

    @guard("Worksheet.calculate")
    def calculate(self):
        self.invalidate()
        try:
            selected = [WORKSHEET_TYPES[self.types.row(item)] for item in self.types.selectedItems()]
            self.items = worksheet(selected, self.difficulty.value(), self.count.value(), self.seed.value())
            self.preview.setHtml(worksheet_html(self.items))
            self.save_questions.setEnabled(True)
            self.save_answers.setEnabled(True)
        except ValueError as exc:
            self.preview.setPlainText(str(exc))

    @guard("Worksheet.save")
    def save(self, answers):
        if self.items:
            path, _ = QFileDialog.getSaveFileName(self, "Save answer key" if answers else "Save worksheet",
                                                "answers.html" if answers else "worksheet.html", "HTML (*.html)")
            if path:
                Path(path).write_text(worksheet_html(self.items, answers=answers), encoding="utf-8")


class FretboardPage(ToolPage):
    def __init__(self, ctx):
        super().__init__(ctx, "Explore sounding notes on fretted instruments. Enter strings in your preferred display order; "
                         "presets run low-string to high-string (ukulele keeps its high G). Fret 0 is relative to the capo. "
                         "Map labels use sharps; highlight any chord or scale by entering its notes. Click a cell to hear it.")
        self.preset_box = self.field("Preset", combo(list(TUNINGS)))
        self.tuning = self.field("Open strings", QLineEdit(TUNINGS["Guitar"]))
        self.frets = self.field("Frets", spin(1, 24, 12))
        self.capo = self.field("Capo", spin(0, 12, 0))
        self.highlight = self.field("Highlight pitch classes", QLineEdit("C E G"))
        self.button("Build fretboard", self.calculate)
        self.table = QTableWidget()
        self.table.setAccessibleName("Clickable fretboard")
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.cellClicked.connect(self.play_cell)
        self.layout.addWidget(self.table, 2)
        self.report.setMaximumHeight(65)
        self.board = []
        self.preset_box.currentTextChanged.connect(self.preset)
        self.watch([self.tuning, self.frets, self.capo, self.highlight], self.invalidate)
        self.calculate()

    def preset(self, title):
        self.tuning.setText(TUNINGS[title])
        self.calculate()

    def invalidate(self):
        self.board = []
        self.table.setRowCount(0)
        self.report.setPlainText("Inputs changed. Rebuild the map.")

    @guard("Fretboard.calculate")
    def calculate(self):
        self.invalidate()
        try:
            board = fretboard(self.tuning.text(), self.frets.value(), self.capo.value())
            pcs = {n.pc for n in parse_notes(self.highlight.text())} if self.highlight.text().strip() else set()
            self.board = board
            self.table.setRowCount(len(board))
            self.table.setColumnCount(len(board[0]))
            self.table.setHorizontalHeaderLabels([str(i) for i in range(len(board[0]))])
            self.table.setVerticalHeaderLabels([f"String {i + 1}" for i in range(len(board))])
            for r, row in enumerate(board):
                for c, note in enumerate(row):
                    item = QTableWidgetItem(note.name)
                    if note.pc in pcs:
                        item.setBackground(QColor(theme.ACCENT))
                        item.setForeground(QColor("#111111"))
                    self.table.setItem(r, c, item)
            self.table.resizeColumnsToContents()
            self.report.setPlainText("Map ready. Highlights match pitch class, including enharmonic equivalents.")
        except ValueError as exc:
            self.report.setPlainText(str(exc))

    @guard("Fretboard.play")
    def play_cell(self, row, column):
        if self.board:
            n = self.board[row][column]
            self.ctx.engine.play_note(n.midi, dur=.6)
            self.report.setPlainText(f"String {row + 1}, fret {column}: {n.name} (MIDI {n.midi})")


class PracticeToolsScreen(QWidget):
    def __init__(self, ctx):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 16)
        layout.addWidget(heading("Practice tools"))
        self.tabs = QTabWidget()
        for title, page in (("Transpose", TransposePage), ("Find scales", ScaleFinderPage),
                            ("Metronome", MetronomePage), ("Worksheets", WorksheetPage),
                            ("Fretboard", FretboardPage)):
            self.tabs.addTab(page(ctx), title)
        layout.addWidget(self.tabs)
