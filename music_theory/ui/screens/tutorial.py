"""Action-checked onboarding using the real editor and an isolated score store."""
from copy import copy, deepcopy

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QStackedWidget,
    QScrollArea, QGridLayout, QProgressBar,
)

from ...theory.part_writing.models import Voice
from ...theory.part_writing.serialization import problem_from_dict, problem_to_dict
from ...theory.pitch import Note
from ..workspace import GUIDES, install_workspace
from .part_writing import PartWritingScreen


class TutorialStore:
    """No tutorial action can write to the learner's assignment or coursework."""
    def __init__(self):
        self.values = {}

    def kv_get(self, key, default=None):
        return deepcopy(self.values.get(key, default))

    def kv_set(self, key, value):
        self.values[key] = deepcopy(value)


STEPS = (
    ("Choose your voice", "Click Bass above the score.",
     "Soprano and Alto share the upper staff. Tenor and Bass share the lower staff. Choosing a voice gives each note its own identity."),
    ("Give the harmony a foundation", "Click the ring to place C3 in chord 1.",
     "C3 sits in the second space from the bottom of the bass staff. The two dots of the bass clef surround the F3 line. Hover first to preview the pitch."),
    ("Move to the next chord", "Place F3 in chord 2, at the new ring.",
     "Each numbered column is one harmony. In C major, IV has F in the bass here. Clicking another column selects it automatically."),
    ("Make a correction", "Right-click chord 2 to remove its Bass note. Or focus the staff and press Delete.",
     "Removing a note affects only the selected voice. Other voices stay intact. Click the correct position whenever you need to replace a pitch."),
    ("Find the missing voices", "Put F3 back in chord 2, then press Solve harmony.",
     "Your notes are clues. The solver searches for complete four-part versions that satisfy the selected rules. It can return several musical possibilities."),
    ("Hear the result", "Press Play all below the score.",
     "Follow each voice as the chords change. If you cannot hear it, check your system volume and Settings → audio output. Play voice and Play chord are in Listen & files."),
    ("Read the assignment", "Open the Assignment tab.",
     "This table stores harmony labels, durations, notes and locks. Write is for the score; Assignment is for precise clues; Practice & rules controls generation; Listen & files contains playback and exports."),
)


class TutorialScreen(QWidget):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self.navigate = None
        self.lab = None
        self.step = 0
        self.heard = False
        self.passed = False
        self._last_save = None
        root = QVBoxLayout(self); root.setContentsMargins(22, 18, 22, 18)
        self.stack = QStackedWidget(); root.addWidget(self.stack)
        self.hub = QScrollArea(); self.hub.setWidgetResizable(True)
        content = QWidget(); box = QVBoxLayout(content); box.setSpacing(18)
        self.hub.setWidget(content); self.stack.addWidget(self.hub)
        tag = QLabel("WELCOME TO YOUR CONSERVATORY"); tag.setObjectName("Kicker"); box.addWidget(tag)
        title = QLabel("A confident first note."); title.setObjectName("WorkspaceTitle"); box.addWidget(title)
        intro = QLabel("Learn the real controls by making music. Your first harmony takes about 4 minutes, and you can pause at any step. The tutorial has its own practice score; your assignments and progress stay safe.")
        intro.setWordWrap(True); box.addWidget(intro)
        row = QHBoxLayout()
        self.start_btn = QPushButton("Start your first harmony  →"); self.start_btn.clicked.connect(self.start)
        row.addWidget(self.start_btn)
        self.restart_btn = QPushButton("Restart tutorial"); self.restart_btn.setObjectName("Secondary"); self.restart_btn.clicked.connect(lambda: self.start(restart=True)); row.addWidget(self.restart_btn)
        skip = QPushButton("Explore on my own"); skip.setObjectName("Secondary"); skip.clicked.connect(self.leave); row.addWidget(skip)
        box.addLayout(row)
        self.context = QLabel(); self.context.setWordWrap(True); self.context.setObjectName("CoachStep"); box.addWidget(self.context)
        label = QLabel("A guide to every workspace"); label.setObjectName("CoachTitle"); box.addWidget(label)
        grid = QGridLayout(); grid.setSpacing(12)
        names = {"dashboard": "Home", "session": "Learn", "practice": "Practice & Dictation", "part_writing": "Part Writing", "piano": "Piano", "reference": "Reference", "tools": "Tools", "studio": "Studio", "stats": "Progress", "achievements": "Awards", "placement": "Placement", "settings": "Settings"}
        for i, (key, name) in enumerate(names.items()):
            card = QWidget(); card.setObjectName("WorkspaceCanvas"); layout = QVBoxLayout(card)
            button = QPushButton(name.replace("&", "&&") + "  →"); button.setObjectName("ModuleCard")
            button.clicked.connect(lambda checked=False, k=key: self.open_workspace(k)); layout.addWidget(button)
            description = QLabel("\n\n".join(f"{n}. {text}" for n, text in enumerate(GUIDES[key][3], 1)))
            description.setWordWrap(True); description.setObjectName("Subtle"); layout.addWidget(description)
            grid.addWidget(card, i // 3, i % 3)
        box.addLayout(grid)
        self.timer = QTimer(self); self.timer.setInterval(200); self.timer.timeout.connect(self.validate)
        self.on_show()

    def on_show(self):
        saved = self.ctx.db.kv_get("tutorial.harmony", {})
        self.start_btn.setText("Replay your first harmony  →" if saved.get("complete") else
                               "Resume your first harmony  →" if saved else "Start your first harmony  →")
        self.restart_btn.setVisible(bool(saved) and not saved.get("complete"))
        if self.lab and self.stack.currentWidget() is self.lab:
            self.timer.start()

    def show_guide(self, key):
        self.timer.stop()
        if key in GUIDES:
            self.context.setText(GUIDES[key][0] + "\n" + "\n".join(GUIDES[key][3]))
        self.stack.setCurrentWidget(self.hub)

    def open_workspace(self, key):
        self.ctx.settings.set("onboarding_seen", True)
        if self.navigate: self.navigate(key)

    def leave(self):
        self.ctx.settings.set("onboarding_seen", True)
        if self.stack.currentWidget() is self.lab: self.save()
        if self.navigate: self.navigate("dashboard")

    def start(self, checked=False, *, restart=False):
        if self.lab is not None:
            if self.lab._thread is not None and self.lab._thread.isRunning():
                self.lab.status.setText("Press Stop and wait for the search to finish before restarting the tutorial.")
                return
            self.stack.removeWidget(self.lab); self.lab.deleteLater()
        sandbox = copy(self.ctx); sandbox.db = TutorialStore()
        saved = {} if restart else self.ctx.db.kv_get("tutorial.harmony", {})
        if saved.get("complete"): saved = {}
        if saved.get("problem"):
            try:
                restored = problem_from_dict(saved["problem"])
                sandbox.db.kv_set("part_writing.autosave", problem_to_dict(restored))
            except (ValueError, TypeError, KeyError):
                saved = {}
        self.step = min(4, max(0, int(saved.get("step", 0))))
        self.heard = False
        self.lab = PartWritingScreen(sandbox)
        if self.step > 0: self.lab._choose_voice(Voice.BASS)
        install_workspace(self.lab, "part_writing")
        self.lab.layout().setContentsMargins(0, 0, 0, 0)
        self.lab.workspace_header.findChild(QLabel, "WorkspaceTitle").setText("Your first harmony.")
        self.lab.workspace_header.findChild(QLabel, "Kicker").setText("GUIDED PRACTICE")
        self.lab.workspace_header.findChild(QLabel, "Subtle").setText("A practice score of your own. Try things, make a correction, and hear what you've built.")
        # Course material stays in the main workspace; the training score is focused.
        self.lab.tabs.tabBar().hide()
        coach = self.lab.coach
        coach.tutorial_mode = True
        coach.tour_button.hide(); coach.detail.hide()
        self.lab.diagnostics.hide()
        for label in coach.steps: label.hide()
        self.progress = QProgressBar(); self.progress.setRange(0, len(STEPS)); self.progress.setTextVisible(False)
        self.progress.setFixedHeight(8)
        coach.box.insertWidget(2, self.progress)
        self.instruction = QLabel(); self.instruction.setWordWrap(True); coach.box.insertWidget(3, self.instruction)
        self.why = QLabel(); self.why.setWordWrap(True); self.why.setObjectName("Subtle"); coach.box.insertWidget(4, self.why)
        self.feedback = QLabel(); self.feedback.setWordWrap(True); self.feedback.setObjectName("AccentValue"); coach.box.insertWidget(5, self.feedback)
        self.previous = QPushButton("Previous"); self.previous.setObjectName("Secondary"); self.previous.clicked.connect(self.back); coach.box.addWidget(self.previous)
        self.next_btn = QPushButton("Continue  →"); self.next_btn.clicked.connect(self.advance); coach.box.addWidget(self.next_btn)
        pause = QPushButton("Pause && leave"); pause.setObjectName("Secondary"); pause.clicked.connect(self.leave); coach.box.addWidget(pause)
        self.lab.play_btn.clicked.connect(self.played)
        self.stack.addWidget(self.lab); self.stack.setCurrentWidget(self.lab)
        self.ctx.settings.set("onboarding_seen", True)
        self.show_step(); self.timer.start()

    def played(self):
        if self.step == 5 and self.lab.solutions: self.heard = True
        self.validate()

    def show_step(self):
        title, instruction, why = STEPS[self.step]
        self.lab.coach.kicker.setText(f"STEP {self.step + 1} / {len(STEPS)}")
        self.lab.coach.title.setText(title)
        self.instruction.setText(instruction); self.why.setText(why)
        self.progress.setValue(self.step); self.previous.setEnabled(self.step > 0)
        self.next_btn.setText("Finish tutorial  ✓" if self.step == len(STEPS)-1 else "Continue  →")
        self.lab.staff.tutorial_target = (0, Voice.BASS, Note.parse("C3")) if self.step == 1 else (1, Voice.BASS, Note.parse("F3")) if self.step in (2, 4) else None
        self.lab.staff.update()
        if self.step < 6: self.lab.editor_tabs.setCurrentIndex(0)
        self.validate()

    def validate(self):
        if not self.lab: return
        def pitch(slot):
            if slot >= len(self.lab.problem.slots): return ""
            note = self.lab.problem.slots[slot].voice(Voice.BASS).pitch.exact
            return note.name if note else ""
        checks = (self.lab.staff.selected_voice == Voice.BASS, pitch(0) == "C3",
                  pitch(1) == "F3", not pitch(1),
                  pitch(0) == "C3" and pitch(1) == "F3" and bool(self.lab.solutions),
                  self.heard, self.lab.editor_tabs.currentIndex() == 1)
        self.passed = checks[self.step]
        self.next_btn.setEnabled(self.passed)
        successes = ("Bass selected. The lower staff is ready for your note.",
                     "C3 is in the right space. Your first bass note is in place.",
                     "F3 is on the right line. It supports the IV chord.",
                     "That note is removed. A blank voice is an open clue.",
                     f"{len(self.lab.solutions)} completions found. Your C3 and F3 clues are preserved.",
                     "Playback requested. Listen for the bass line you wrote.",
                     "Here are your exact clues and harmony labels. You're ready to use the workspace.")
        message = "✓ " + successes[self.step] if self.passed else "Try the action above to continue."
        if not self.passed and self.step in (1, 2):
            actual = pitch(0 if self.step == 1 else 1)
            if actual: message = f"You placed {actual}. Click the ring to replace it with {'C3' if self.step == 1 else 'F3'}."
        if self.step == 4 and self.lab._thread is not None: message = "Searching for complete harmonies…" if not self.passed else message
        self.feedback.setText(message)
        self.save()

    def save(self, complete=False):
        if not self.lab: return
        value = {"step": self.step, "problem": problem_to_dict(self.lab.problem), "complete": complete}
        if value != self._last_save:
            self.ctx.db.kv_set("tutorial.harmony", value); self._last_save = deepcopy(value)

    def back(self):
        self.step = max(0, self.step - 1); self.show_step()

    def advance(self):
        if not self.passed: return
        if self.step == len(STEPS)-1:
            self.timer.stop(); self.save(complete=True)
            self.context.setText("✓ First harmony complete. You can select voices, place and correct notes, solve missing parts, play the result and edit assignment clues. Choose a workspace below to use what you learned.")
            self.stack.setCurrentWidget(self.hub); self.on_show()
        else:
            self.step += 1; self.show_step()

    def hideEvent(self, event):
        self.timer.stop(); self.ctx.engine.stop()
        if self.lab and self.lab._cancel is not None: self.lab._cancel.set()
        super().hideEvent(event)

    def closeEvent(self, event):
        self.timer.stop()
        if self.lab: self.lab.close()
        super().closeEvent(event)
