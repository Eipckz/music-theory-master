"""Small, offline assignment calculators embedded in Reference."""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QPushButton, QPlainTextEdit, QApplication

from ...theory.workbench import analyze_notes, analyze_rhythm


class Workbench(QWidget):
    def __init__(self, ctx, *, rhythm=False, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.rhythm = rhythm
        self.midis = []
        layout = QVBoxLayout(self)
        help_text = ("Count durations exactly: w whole, h half, q quarter, e eighth, s sixteenth, x thirty-second. "
                     "Add . or .. for dots; r marks a rest (rq); t(e) is one eighth-note triplet. "
                     "Fractions such as 1/8 are fractions of a whole note. Separate bars with |."
                     if rhythm else "Enter the notes you have, with their original spelling: C4 E4 G4 Bb4 D5. "
                     "Spaces or commas separate notes; omitted octaves default to 4. "
                     "Up to 64 notes can be analyzed; this tool does not require four voices.")
        help_label = QLabel(help_text)
        help_label.setWordWrap(True)
        layout.addWidget(help_label)
        row = QHBoxLayout()
        row.addWidget(QLabel("Meter" if rhythm else "Tonic"))
        self.context_input = QLineEdit("4/4" if rhythm else "C")
        self.context_input.setMaximumWidth(90)
        self.context_input.setAccessibleName("Meter" if rhythm else "Tonic")
        row.addWidget(self.context_input)
        self.mode = QComboBox()
        self.mode.addItems(["major", "minor"])
        self.mode.setAccessibleName("Key mode")
        self.mode.setVisible(not rhythm)
        row.addWidget(self.mode)
        row.addStretch()
        layout.addLayout(row)
        self.input = QLineEdit("q q h | t(e) t(e) t(e) q h" if rhythm else "G3 B3 D4 F4")
        self.input.setAccessibleName("Durations" if rhythm else "Supplied pitches")
        layout.addWidget(self.input)
        buttons = QHBoxLayout()
        calculate = QPushButton("Check bars" if rhythm else "Analyze notes")
        calculate.clicked.connect(self.calculate)
        self.input.returnPressed.connect(self.calculate)
        buttons.addWidget(calculate)
        self.play = QPushButton("Play chord")
        self.play.clicked.connect(lambda: self.ctx.engine.play_chord(self.midis, tempo=80) if self.midis else None)
        self.play.setVisible(not rhythm)
        buttons.addWidget(self.play)
        copy = QPushButton("Copy report")
        copy.clicked.connect(lambda: QApplication.clipboard().setText(self.report.toPlainText()))
        buttons.addWidget(copy)
        buttons.addStretch()
        layout.addLayout(buttons)
        self.report = QPlainTextEdit()
        self.report.setReadOnly(True)
        self.report.setAccessibleName("Analysis report")
        layout.addWidget(self.report, 1)
        self.input.textChanged.connect(self.invalidate)
        self.context_input.textChanged.connect(self.invalidate)
        self.mode.currentTextChanged.connect(self.invalidate)
        self.calculate()

    def invalidate(self):
        self.midis = []
        self.play.setEnabled(False)
        self.report.setPlainText("Inputs changed. Calculate again to update the report.")

    def calculate(self):
        self.midis = []
        self.play.setEnabled(False)
        try:
            if self.rhythm:
                _, report = analyze_rhythm(self.input.text(), self.context_input.text())
            else:
                self.midis, report = analyze_notes(self.input.text(), self.context_input.text(), self.mode.currentText())
            self.report.setPlainText(report)
            self.play.setEnabled(bool(self.midis))
        except Exception as exc:
            self.report.setPlainText(f"Input problem: {exc}")
