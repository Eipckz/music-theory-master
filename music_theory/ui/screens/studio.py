"""Score, singing, jazz and teacher practice share one offline studio."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from html import unescape
from pathlib import Path

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget,
    QLineEdit, QComboBox, QListWidget, QAbstractItemView, QFileDialog,
    QDoubleSpinBox, QGridLayout, QPushButton,
)

from ...errors import guard
from ...audio.pitch_tracking import track_pitch, load_wav, intonation_report, compare_melody
from ...audio.recording import MicrophoneRecorder
from ...theory.pitch import Note
from ...theory.score_study import load_score, passage, playback_events, monophonic_line, review_voice_leading
from ...theory.jazz import ii_v_i, shell_voicings
from ...exercises.base import Exercise, InputMode
from ...exercises.registry import title_of
from ...exercises.assignments import (
    ASSIGNMENT_TYPES, create_assignment, load_assignment, save_json,
    unpack_exercise, make_result, read_json, check_result,
)
from .. import theme
from ..common import heading
from ..exercise_player import ExercisePlayer
from ..widgets import StaffWidget
from .practice_tools import ToolPage, combo, spin

_ANALYSIS_POOL = ThreadPoolExecutor(max_workers=1, thread_name_prefix="pitch-analysis")


class StudioPage(ToolPage):
    """Keep the longer Studio action lists usable on small laptop screens."""
    def __init__(self, ctx, help_text):
        super().__init__(ctx, help_text)
        self.layout.removeItem(self.buttons)
        self.buttons.deleteLater()
        self.buttons = QGridLayout()
        self.layout.insertLayout(2, self.buttons)
        self.button_count = 0

    def button(self, title, handler):
        button = QPushButton(title)
        button.clicked.connect(handler)
        self.buttons.addWidget(button, self.button_count // 3, self.button_count % 3)
        self.button_count += 1
        return button

    def hideEvent(self, event):
        self.ctx.engine.stop()
        super().hideEvent(event)


class PitchTrace(QWidget):
    def __init__(self):
        super().__init__()
        self.frames = []
        self.target = 69
        self.setMinimumHeight(150)
        self.setAccessibleName("Pitch trace: time horizontally, MIDI pitch vertically")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(theme.SURFACE))
        values = [f.midi for f in self.frames if f.midi is not None]
        low = min(values + [self.target - 2]) - 1
        high = max(values + [self.target + 2]) + 1
        width, height = self.width() - 60, self.height() - 35
        end = max([f.time for f in self.frames] + [1.])
        def point(t, midi):
            return 45 + t / end * width, 10 + (high - midi) / (high - low) * height
        painter.setPen(QPen(QColor(theme.TEXT_MUTED), 1))
        _, y = point(0, self.target)
        painter.drawLine(45, int(y), self.width() - 10, int(y))
        painter.drawText(4, int(y), str(self.target))
        painter.drawText(45, self.height() - 3, "0 s")
        painter.drawText(self.width() - 60, self.height() - 3, f"{end:.1f} s")
        painter.setPen(QPen(QColor(theme.ACCENT), 2))
        previous = None
        for frame in self.frames:
            if frame.midi is None:
                previous = None
                continue
            x, y = point(frame.time, frame.midi)
            if previous:
                painter.drawLine(int(previous[0]), int(previous[1]), int(x), int(y))
            previous = (x, y)


class SingingPage(StudioPage):
    def __init__(self, ctx):
        super().__init__(ctx, "Sing one voice or play one instrument. Start explicitly records locally for the selected duration; "
                         "nothing is uploaded or automatically saved. Use headphones for a reference. Pitch tracking is an estimate, "
                         "not a singing-technique grade; chords, noise and breath can make it unreliable.")
        self.target = self.field("Target note", QLineEdit("A4"))
        self.seconds = self.field("Recording seconds", spin(1, 30, 5))
        self.device = self.field("Microphone", QComboBox())
        self.device.addItem("System default", None)
        self.tolerance = self.field("Tolerance (cents)", spin(5, 100, 35))
        self.offset = QDoubleSpinBox()
        self.offset.setRange(-10, 10)
        self.offset.setSingleStep(.1)
        self.field("Melody alignment (seconds)", self.offset)
        self.button("Input devices", self.refresh_devices)
        self.button("Hear target", self.hear)
        self.record_btn = self.button("Record", self.record)
        self.button("Stop", self.stop)
        self.button("Open WAV", self.open_wav)
        self.button("Compare again", self.analyze)
        self.button("Clear score melody", self.clear_melody)
        self.recorder = MicrophoneRecorder()
        self.record_timer = QTimer(self)
        self.record_timer.setSingleShot(True)
        self.record_timer.timeout.connect(self.stop)
        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(75)
        self.poll_timer.timeout.connect(self.poll)
        self.samples = None
        self.rate = 16000
        self.expected = []
        self.future = None
        self.frames = []
        self.trace = PitchTrace()
        self.layout.addWidget(self.trace)
        self.watch([self.target, self.tolerance], self.invalidate)
        self.offset.valueChanged.connect(self.invalidate)

    def invalidate(self):
        self.poll_timer.stop()
        if self.future:
            self.future.cancel()
        self.future = None
        self.frames = []
        self.trace.frames = []
        self.trace.update()
        self.report.setPlainText("Inputs changed. Compare again after recording or loading WAV.")

    @guard("Singing.devices")
    def refresh_devices(self):
        self.device.clear()
        self.device.addItem("System default", None)
        try:
            for index, name in MicrophoneRecorder.devices():
                self.device.addItem(name, index)
        except Exception as exc:
            self.report.setPlainText(f"Microphone devices unavailable: {exc}. WAV import remains available.")

    @guard("Singing.hear")
    def hear(self):
        self.ctx.engine.play_note(Note.parse(self.target.text()).midi)

    @guard("Singing.record")
    def record(self):
        self.stop_recording(discard=True)
        self.invalidate()
        self.samples = None
        self.ctx.engine.stop()
        try:
            self.recorder.start(self.device.currentData(), self.seconds.value())
            self.record_timer.start(self.seconds.value() * 1000)
            self.record_btn.setEnabled(False)
            self.report.setPlainText("Recording locally… Stop ends capture and analyzes it. Leaving this page discards the recording.")
        except Exception as exc:
            self.report.setPlainText(f"Cannot open microphone: {exc}. Check OS microphone permissions/device selection, or open a WAV recording.")

    def stop_recording(self, discard=False):
        self.record_timer.stop()
        if self.recorder.stream is not None:
            samples, rate = self.recorder.stop()
            if not discard:
                self.samples, self.rate = samples, rate
        self.record_btn.setEnabled(True)

    @guard("Singing.stop")
    def stop(self):
        self.stop_recording()
        if self.samples is not None:
            self.analyze()

    @guard("Singing.open")
    def open_wav(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open monophonic recording", "", "WAV audio (*.wav)")
        if path:
            self.stop_recording(discard=True)
            self.invalidate()
            self.samples = None
            try:
                self.samples, self.rate = load_wav(Path(path))
                self.analyze()
            except ValueError as exc:
                self.report.setPlainText(str(exc))

    @guard("Singing.analyze")
    def analyze(self):
        if self.samples is None:
            self.report.setPlainText("Record a note or open WAV first.")
            return
        self.invalidate()
        self.future = _ANALYSIS_POOL.submit(track_pitch, self.samples.copy(), self.rate)
        self.poll_timer.start()
        self.report.setPlainText("Analyzing local audio…")

    @guard("Singing.poll")
    def poll(self):
        if self.future is None or not self.future.done():
            return
        self.poll_timer.stop()
        future, self.future = self.future, None
        try:
            self.frames = future.result()
            target = Note.parse(self.target.text()).midi
            result = intonation_report(self.frames, target, self.tolerance.value())
            lines = [f"Voiced frames: {result['voiced_frames']}/{result['total_frames']}"]
            if result["voiced_frames"]:
                lines += [f"Median offset: {result['median_cents']:+.1f} cents (positive = sharp)",
                          f"Within ±{self.tolerance.value()} cents: {result['within_percent']}% of voiced frames",
                          f"10–90% pitch spread: {result['spread_cents']} cents"]
            lines.append(result["message"])
            if self.expected:
                comparison = compare_melody(self.frames, self.expected, offset=self.offset.value(), tolerance=self.tolerance.value())
                lines += ["", "Imported melody comparison (alignment is manual):"]
                for i, note in enumerate(comparison, 1):
                    cents = "unvoiced" if note["median_cents"] is None else f"{note['median_cents']:+.1f} cents"
                    lines.append(f"Note {i}, MIDI {note['target']}: {cents}; {'matched' if note['matched'] else 'review'}")
            self.report.setPlainText("\n".join(lines))
            self.trace.frames, self.trace.target = self.frames, target
            self.trace.update()
        except Exception as exc:
            self.report.setPlainText(f"Cannot analyze recording: {exc}")

    def set_melody(self, events, bpm):
        line = monophonic_line(events)
        if len(line) > 256:
            raise ValueError("Select at most 256 notes for singing comparison.")
        self.invalidate()
        start = line[0].offset
        self.expected = [((e.offset - start) * 60 / bpm, e.duration * 60 / bpm, e.notes[0].midi) for e in line]
        self.target.setText(line[0].notes[0].name)
        self.report.setPlainText(f"{len(line)} score notes loaded at {bpm} BPM. Record or load WAV; adjust alignment to your first note as needed. No count-in is recorded.")

    @guard("Singing.clear_melody")
    def clear_melody(self):
        self.expected = []
        self.invalidate()

    def hideEvent(self, event):
        self.stop_recording(discard=True)
        self.ctx.engine.stop()
        self.invalidate()
        super().hideEvent(event)


class ScorePage(StudioPage):
    def __init__(self, ctx, singing):
        super().__init__(ctx, "Import a local MusicXML/MXL score. Select parts, measures and a voice. Playback retains internal rests and note lengths, "
                         "starts at the first selected attack, and uses written pitches at constant tempo. Repeats/ornaments/percussion are not performed.")
        self.singing = singing
        self.score = None
        self.imported = ()
        self.open_btn = self.button("Open MusicXML", self.open)
        self.parts = QListWidget()
        self.parts.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.parts.setMaximumHeight(90)
        self.field("Parts", self.parts)
        self.first = self.field("First measure", spin(0, 9999, 1))
        self.last = self.field("Last measure", spin(0, 9999, 4))
        self.voice = self.field("Voice within selected parts", QComboBox())
        self.voice.addItem("All voices", None)
        self.bpm = self.field("Tempo (quarter-note BPM)", spin(20, 240, 90))
        self.leap = self.field("Flag melodic leaps above (semitones)", spin(1, 24, 12))
        self.button("Play passage", self.play)
        self.button("Stop", self.ctx.engine.stop)
        self.button("Review voice leading", self.review)
        self.button("Practice pitches", self.practice)
        self.button("Send to singing", self.send_singing)
        self.staff = StaffWidget("treble")
        self.staff.setMinimumHeight(130)
        self.layout.addWidget(self.staff)
        self.player = ExercisePlayer(ctx.engine, ctx.midi, settings=ctx.settings)
        self.player.hide()
        self.layout.addWidget(self.player)
        self.watch([self.first, self.last, self.voice, self.bpm, self.leap], self.invalidate)
        self.parts.itemSelectionChanged.connect(self.invalidate)

    def invalidate(self):
        self.ctx.engine.stop()
        self.player.hide()
        self.staff.set_notes([])
        if self.score:
            self.report.setPlainText(f"{self.score.title}: selection changed. Play, review or practice the selected passage.")

    @guard("Score.open")
    def open(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open score", "", "MusicXML (*.musicxml *.xml *.mxl)")
        if path:
            self.load(Path(path))

    def load(self, path):
        self.invalidate()
        self.score = None
        self.parts.clear()
        self.voice.clear()
        self.voice.addItem("All voices", None)
        try:
            score = load_score(path)
            self.score = score
            self.parts.addItems(score.parts)
            for i in range(self.parts.count()):
                self.parts.item(i).setSelected(True)
            for v in sorted({e.voice for e in score.events}):
                self.voice.addItem(v, v)
            self.first.setValue(min(e.measure for e in score.events))
            self.last.setValue(min(max(e.measure for e in score.events), self.first.value() + 7))
            self.report.setPlainText(f"{score.title}\n{len(score.parts)} parts; {len(score.events)} pitched events.\n" + "\n".join(score.warnings))
        except ValueError as exc:
            self.report.setPlainText(str(exc))

    def selected(self):
        if self.score is None:
            raise ValueError("Open a MusicXML score first.")
        events = passage(self.score, [p.text() for p in self.parts.selectedItems()], self.first.value(), self.last.value())
        voice = self.voice.currentData()
        if voice is not None:
            events = tuple(e for e in events if e.voice == voice)
        if not events:
            raise ValueError("No notes in this voice selection.")
        return events

    @guard("Score.play")
    def play(self):
        try:
            events = self.selected()
            self.ctx.engine.play_events(playback_events(events, self.bpm.value()))
            self.staff.set_notes([n for e in events[:16] for n in e.notes])
        except ValueError as exc:
            self.report.setPlainText(str(exc))

    @guard("Score.review")
    def review(self):
        try:
            issues, skipped = review_voice_leading(self.selected(), leap_limit=self.leap.value())
            lines = ["Checks: parallel perfect fifths/octaves/unisons between independent monophonic lines; melodic leaps above the selected threshold.",
                     "This does not check all counterpoint, harmony, dissonance preparation or style-specific conventions.", ""]
            lines += [f"Measure {i.measure}, score quarter offset {i.beat:g}: {i.rule}\n  {i.voices}: {i.detail}" for i in issues]
            if not issues:
                lines.append("No findings under these selected checks. This is not proof of complete stylistic correctness.")
            lines += skipped
            self.report.setPlainText("\n".join(lines))
        except ValueError as exc:
            self.report.setPlainText(str(exc))

    @guard("Score.practice")
    def practice(self):
        try:
            events = monophonic_line(self.selected())
            if len(events) > 32:
                raise ValueError("Select at most 32 notes for pitch-entry practice.")
            notes = [e.notes[0] for e in events]
            ex = Exercise(skill_id="score.practice", domain="aural", etype="score_melody",
                          prompt="Listen with Play passage, then enter this imported melody's pitches in order. Rhythm is not graded.",
                          input_mode=InputMode.NOTE_ENTRY, answer=[n.midi for n in notes], difficulty=4,
                          explanation="Melody: " + " ".join(n.name for n in notes),
                          tags={"match": "exact", "staff_prompt": {"clef": "treble", "notes": []}},
                          reveal={"staff": {"clef": "treble", "notes": notes}})
            self.player.set_exercise(ex, show_next=False)
            self.player.show()
            self.staff.set_notes([])
            self.report.setPlainText("Imported practice is ungraded course work: no XP or mastery is changed.")
        except ValueError as exc:
            self.report.setPlainText(str(exc))

    @guard("Score.singing")
    def send_singing(self):
        try:
            self.singing.set_melody(self.selected(), self.bpm.value())
            self.report.setPlainText("Passage sent to Singing. Open that tab to record or compare WAV.")
        except ValueError as exc:
            self.report.setPlainText(str(exc))

    def hideEvent(self, event):
        self.ctx.engine.stop()
        super().hideEvent(event)


class JazzPage(StudioPage):
    def __init__(self, ctx):
        super().__init__(ctx, "Explore a standard ii–V–I or tritone-substituted path. Compare full chords with root/third/seventh shells. "
                         "Minor examples use i7; minor-sixth and minor-major-seventh tonics are other stylistic choices. Lessons and graded drills are in Learn/Practice.")
        self.tonic = self.field("Tonic", combo(["C", "F", "G", "Bb", "D", "Eb", "A", "Ab", "E", "Db", "B", "F#"]))
        self.mode = self.field("Mode", combo(["Major", "Minor"]))
        self.sub = self.field("Dominant", combo(["Standard V7", "Tritone substitute ♭II7"]))
        self.voicing = self.field("Voicing", combo(["Shells", "Full chords"]))
        self.bpm = self.field("Tempo", spin(30, 180, 75))
        self.button("Build progression", self.calculate)
        self.play_btn = self.button("Hear progression", self.play)
        self.staff = StaffWidget("grand")
        self.layout.addWidget(self.staff)
        self.chords = []
        self.watch([self.tonic, self.mode, self.sub, self.voicing, self.bpm], self.calculate)
        self.calculate()

    @guard("Jazz.build")
    def calculate(self):
        self.ctx.engine.stop()
        chords = ii_v_i(Note.parse(self.tonic.currentText() + "4"), minor=self.mode.currentIndex() == 1, substitute=self.sub.currentIndex() == 1)
        self.chords = shell_voicings(chords) if self.voicing.currentIndex() == 0 else [list(c.notes) for c in chords]
        self.report.setPlainText("\n\n".join(f"{c.label}: {' '.join(n.name_no_octave for n in c.notes)}\nGuide tones: {' '.join(n.name_no_octave for n in c.guides)}\nVoicing: {' '.join(n.name for n in v)}" for c, v in zip(chords, self.chords)))
        self.staff.set_columns(self.chords, durations=[2, 2, 2])

    @guard("Jazz.play")
    def play(self):
        self.ctx.engine.play_sequence([([n.midi for n in chord], 2) for chord in self.chords], tempo=self.bpm.value())


class AssignmentPage(StudioPage):
    def __init__(self, ctx):
        super().__init__(ctx, "Create an offline assignment, share its JSON file, complete it here, then return a result file. "
                         "Teachers can regrade responses against the original assignment. Files contain the answer key; identity and testing conditions are not verified. No network or course XP is involved.")
        self.title = self.field("Assignment title", QLineEdit("Musicianship practice"))
        self.learner = self.field("Learner name (optional)", QLineEdit())
        self.topic = self.field("Topic", combo([title_of(t) for t in ASSIGNMENT_TYPES]))
        self.difficulty = self.field("Difficulty", spin(0, 10, 4))
        self.count = self.field("Questions", spin(1, 50, 8))
        self.seed = self.field("Seed", spin(0, 999999, 1234))
        self.button("Create", self.create)
        self.button("Open assignment", self.open)
        self.button("Save assignment", self.save)
        self.button("Start / restart", self.start)
        self.button("Export result", self.export)
        self.button("Check result file", self.check)
        self.assignment = None
        self.exercises = []
        self.responses = []
        self.index = 0
        self.player = ExercisePlayer(ctx.engine, ctx.midi, settings=ctx.settings)
        self.player.hide()
        self.layout.addWidget(self.player)
        self.watch([self.title, self.topic, self.difficulty, self.count, self.seed], self.invalidate)

    def invalidate(self):
        self.ctx.engine.stop()
        self.assignment = None
        self.exercises = []
        self.responses = []
        self.index = 0
        self.player.hide()
        self.report.setPlainText("Creation settings changed. Create a new assignment or open a saved one.")

    @guard("Assignments.create")
    def create(self):
        self.invalidate()
        try:
            self.assignment = create_assignment(self.title.text(), [ASSIGNMENT_TYPES[self.topic.currentIndex()]], self.difficulty.value(), self.count.value(), self.seed.value())
            self.exercises = [unpack_exercise(item) for item in self.assignment["items"]]
            self.report.setPlainText(f"Created {len(self.exercises)} questions. Save to share, or Start to practice.")
        except ValueError as exc:
            self.report.setPlainText(str(exc))

    @guard("Assignments.open")
    def open(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open assignment", "", "Assignment JSON (*.json)")
        if path:
            self.invalidate()
            try:
                self.assignment, self.exercises = load_assignment(Path(path))
                self.report.setPlainText(f"Loaded: {self.assignment['title']}\n{len(self.exercises)} questions. Press Start.")
            except Exception as exc:
                self.report.setPlainText(f"Cannot load assignment: {exc}")

    @guard("Assignments.save")
    def save(self):
        if self.assignment:
            path, _ = QFileDialog.getSaveFileName(self, "Save assignment", "practice.mtm-assignment.json", "JSON (*.json)")
            if path:
                save_json(Path(path), self.assignment)

    @guard("Assignments.start")
    def start(self):
        if self.assignment:
            self.responses = []
            self.index = 0
            self.load_next()

    def load_next(self):
        if self.index >= len(self.exercises):
            self.player.hide()
            result = make_result(self.assignment, self.learner.text(), self.responses)
            self.report.setPlainText(f"Completed: {result['correct']}/{result['total']}. Export result to share.\n{result['notice']}")
            return
        ex = self.exercises[self.index]
        self.player.set_exercise(ex, on_answer=self.answered, on_next=self.advance, badge=f"Assignment question {self.index + 1}/{len(self.exercises)}")
        self.player.prompt.setTextFormat(Qt.TextFormat.PlainText)
        self.player.prompt.setText(unescape(ex.prompt))
        self.player.show()

    @guard("Assignments.answer")
    def answered(self, correct, milliseconds):
        if len(self.responses) == self.index:
            self.responses.append(self.player.last_response)

    @guard("Assignments.next")
    def advance(self):
        if len(self.responses) == self.index + 1:
            self.index += 1
            self.load_next()

    @guard("Assignments.export")
    def export(self):
        if self.assignment:
            try:
                result = make_result(self.assignment, self.learner.text(), self.responses)
                path, _ = QFileDialog.getSaveFileName(self, "Export practice result", "practice.mtm-result.json", "JSON (*.json)")
                if path:
                    save_json(Path(path), result)
            except ValueError as exc:
                self.report.setPlainText(str(exc))

    @guard("Assignments.check")
    def check(self):
        if self.assignment:
            path, _ = QFileDialog.getOpenFileName(self, "Check result against loaded assignment", "", "Result JSON (*.json)")
            if path:
                try:
                    result = check_result(self.assignment, read_json(Path(path)))
                    self.report.setPlainText(f"Regraded {result['learner']}: {result['correct']}/{result['total']}\n{result['notice']}")
                except Exception as exc:
                    self.report.setPlainText(f"Cannot regrade result: {exc}")


class StudioScreen(QWidget):
    def __init__(self, ctx):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 16)
        layout.addWidget(heading("Musicianship studio"))
        self.tabs = QTabWidget()
        self.singing = SingingPage(ctx)
        self.score = ScorePage(ctx, self.singing)
        self.jazz = JazzPage(ctx)
        self.assignments = AssignmentPage(ctx)
        for title, page in (("Score practice & review", self.score), ("Singing", self.singing),
                            ("Jazz", self.jazz), ("Assignments", self.assignments)):
            self.tabs.addTab(page, title.replace("&", "&&"))
        layout.addWidget(self.tabs)
