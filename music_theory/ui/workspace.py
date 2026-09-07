"""Shared conservatory composition: editorial header, task canvas and coach.

Existing screen objects and their controls remain the owners of all actions.
This layer organizes them; it does not duplicate their business logic.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QButtonGroup, QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QTabWidget, QVBoxLayout, QWidget, QSizePolicy,
)


GUIDES = {
    "dashboard": ("YOUR CONSERVATORY", "A little practice. A deeper understanding.", "Choose what you want to make progress on today.",
                  ("Start with Learn for a short lesson and guided practice.", "Use the harmony studio when you have notes or an assignment to work through.", "Your progress grows as you answer exercises. There is no daily penalty.")),
    "session": ("LEARNING PATH", "Understand it. Then make it yours.", "A short explanation, a musical example, and practice that meets you where you are.",
                ("Read the lesson and play its musical examples.", "Try the exercise. Hints explain a method when you are stuck.", "Complete the short session; your next lesson adapts to your answers.")),
    "practice": ("PRACTICE ROOM", "Make it second nature.", "Choose a skill. Take a focused turn. Build confidence one answer at a time.",
                 ("Choose Theory, Ear training or Keyboard, then a topic.", "Keep Adaptive on, or set your own difficulty.", "Answer the question and read the explanation before the next one.")),
    "part_writing": ("PART WRITING STUDIO", "Make room for harmony.", "Write what you know. Hear the possibilities. Understand the resolution.",
                     ("Choose a voice and place its notes directly on the staff.", "Use Assignment for harmony labels, durations and locked clues.", "Solve harmony finds completions; Check explains your writing.")),
    "piano": ("KEYBOARD ROOM", "See the note. Hear the relationship.", "Move between the staff, the keyboard and the sound.",
              ("Choose a root and a scale or chord to hear its shape.", "Click a key to see the pitch on the staff.", "Focus the keyboard: A–L play notes; Z / X shift the octave.")),
    "reference": ("REFERENCE LIBRARY", "Make the connections.", "Explore a musical idea with an explanation you can see and hear.",
                  ("Choose a reference module above.", "Change its notes, key or rhythm to explore the relationship.", "Use the playable examples to connect the explanation to sound.")),
    "tools": ("MUSICIAN'S TOOLKIT", "A clearer way through the details.", "Purpose-built tools for the calculations and practice around your music.",
              ("Choose the tool for your task above.", "Enter your material and check the labeled options.", "Run the main action, inspect the result, then play or export it.")),
    "studio": ("MUSICIANSHIP STUDIO", "Turn study into sound.", "A focused workspace for scores, intonation, jazz and shared practice.",
               ("Choose Score study, Singing, Jazz or Assignments.", "Start with the setup card. Each field describes what the tool needs.", "Use the main action, then inspect the music and feedback below.")),
    "stats": ("YOUR JOURNEY", "See how far you've come.", "Use your progress to choose the next useful thing to practice.",
              ("Compare your theory, listening and keyboard progress.", "Find skills with fewer attempts or lower mastery.", "Return to Practice to work on one of those skills.")),
    "achievements": ("MILESTONES", "Small steps worth remembering.", "A record of the practice and discoveries that brought you here.",
                     ("Browse earned and upcoming milestones.", "Choose a practice goal that fits your next session.", "Achievements celebrate progress; they do not replace mastery.")),
    "placement": ("FIND YOUR STARTING POINT", "Begin where you are.", "A practice recommendation, with room for what you have yet to learn.",
                  ("Choose the areas you want to assess and check sound.", "Use 'I don't know yet' when you are unsure.", "You can skip placement or retake it without losing earned progress.")),
    "settings": ("MAKE IT YOURS", "A comfortable place to practice.", "Tune the sound, display and controls to suit how you work.",
                 ("Choose audio output, instrument and MIDI input if you use one.", "Adjust theme, text size and notation for comfortable reading.", "Changes apply locally. Progress reset is a separate confirmed action.")),
    "about": ("ABOUT THE CONSERVATORY", "Music first. Always offline.", "Your local workspace for learning, listening and making sense of music.",
              ("Check the installed version and application information.", "Use Tutorials for practical introductions to the workspaces.", "Your music and progress stay on this computer unless you export them.")),
}

MODULE_HELP = {
    "Score study": ("Open MusicXML or MXL from your computer.", "Select the parts, voice and measure range you want to study.", "Play the passage, practice its pitches or review voice leading."),
    "Score practice": ("Open a MusicXML or MXL score.", "Choose a voice and measure range.", "Play the passage or practice the notes; inspect located feedback."),
    "Singing": ("Choose the target pitch or use an imported melody.", "Check the microphone and duration, then explicitly press Record—or open a WAV.", "Read sharp/flat feedback as an estimate; use headphones for the reference."),
    "Jazz": ("Choose a tonic and major or minor ii–V–I.", "Compare full chords, shells and a tritone substitution.", "Play the progression and follow the spelled guide tones."),
    "Assignments": ("Create practice questions or open a shared assignment file.", "Start the assignment and answer the questions.", "Export the result; checking a result requires the original assignment."),
    "Circle of fifths": ("Click a key around the circle.", "Read its relative minor and key signature.", "Hear the tonic to connect the notation with its sound."),
    "Explorer": ("Choose a root note and a musical structure.", "Read the spelled notes and their positions on the staff.", "Play the example and change one setting to compare."),
    "Analyze notes": ("Enter spelled pitches, including octaves when relevant.", "Choose the analysis that answers your question.", "Read the result with the displayed spelling, then audition it."),
    "Rhythm & meter": ("Enter durations such as q for quarter and e for eighth notes.", "Choose a meter and calculate the total.", "Compare the result with the measure length; export when it matches."),
    "Post-tonal bridge": ("Choose sets, rows or transformations.", "Enter note names or pitch classes; T and E mean 10 and 11.", "Inspect the clock or matrix and play the result."),
    "Glossary": ("Search for a term or browse the list.", "Read the short explanation.", "Play its example when a listening button is available."),
    "Transposition": ("Enter notes with their spellings and octaves.", "Choose an interval and direction, or an instrument conversion.", "Transpose, inspect the result, then hear or export it."),
    "Scale finder": ("Enter the notes you have.", "Set a tonic if known and how many outside notes to allow.", "Compare possible scales; a collection alone does not establish a key."),
    "Metronome": ("Choose BPM, beat groups and subdivisions.", "Start the click and follow the accented groups.", "Tap to estimate tempo; Stop or leave this page to end playback."),
    "Worksheets": ("Choose a topic, difficulty and question count.", "Generate a reproducible worksheet.", "Save or print the worksheet and its separate answer key."),
    "Fretboard": ("Choose a tuning or enter your own.", "Select a root and scale or chord.", "Read the marked positions and compare the displayed pitches."),
    "Write": ("Pick a voice. Hover for a pitch preview; click to add it.", "Right-click or Delete removes that voice's selected note.", "Solve harmony completes the missing voices. Playback can include partial notes."),
    "Assignment": ("Enter Roman numerals, chord names or figured bass across the columns.", "Add voice clues and lock the notes auto-correction must preserve.", "Use Slot constraints for inversions, alternatives, ranges and clefs."),
    "Practice & rules": ("Choose the practice type and difficulty, then Generate.", "Adjust the rule profile and cadence to match the assignment.", "Search budget and result count control how many completions to explore."),
    "Listen & files": ("Compare solutions with Previous and Next.", "Hear one voice, chord or transition to follow the voice leading.", "Save/Open preserves input clues; MusicXML exports the completed score."),
}
MODULE_HELP["Transpose"] = MODULE_HELP["Transposition"]
MODULE_HELP["Find scales"] = MODULE_HELP["Scale finder"]


def icon_for(name: str) -> QIcon:
    """A small original line-icon family, consistent across all destinations."""
    pm = QPixmap(24, 24); pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm); p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor("#b7cdc7"), 1.5))
    if name in ("part_writing", "reference", "session"):
        for y in (6, 10, 14, 18): p.drawLine(3, y, 21, y)
        p.drawEllipse(9, 10, 5, 4); p.drawLine(14, 12, 14, 3)
    elif name == "piano":
        p.drawRoundedRect(3, 4, 18, 16, 2, 2)
        for x in (7, 12, 17): p.drawLine(x, 4, x, 20)
    elif name in ("stats", "practice", "placement"):
        for x, y in ((5, 13), (11, 8), (17, 4)): p.drawRect(x, y, 3, 20-y)
    elif name in ("studio", "dictation"):
        for x, y in ((4, 9), (8, 4), (12, 7), (16, 2), (20, 9)): p.drawLine(x, y, x, 24-y)
    elif name == "dashboard":
        p.drawLine(3, 11, 12, 3); p.drawLine(12, 3, 21, 11); p.drawRect(6, 11, 12, 10)
    elif name == "tutorial":
        p.drawEllipse(3, 3, 18, 18); p.drawText(8, 17, "?")
    else:
        p.drawRoundedRect(4, 4, 16, 16, 4, 4); p.drawLine(8, 9, 16, 9); p.drawLine(8, 14, 16, 14)
    p.end(); return QIcon(pm)


class CoachPanel(QFrame):
    def __init__(self, screen, key):
        super().__init__(); self.screen = screen; self.key = key
        self.setObjectName("Coach"); self.setMinimumWidth(218); self.setMaximumWidth(262)
        self.box = QVBoxLayout(self); self.box.setContentsMargins(20, 22, 20, 20); self.box.setSpacing(16)
        self.kicker = QLabel("A LITTLE GUIDANCE"); self.kicker.setObjectName("Kicker"); self.kicker.setWordWrap(True); self.box.addWidget(self.kicker)
        self.title = QLabel("Your next step"); self.title.setObjectName("CoachTitle"); self.title.setWordWrap(True); self.box.addWidget(self.title)
        self.steps = []
        for n in range(3):
            label = QLabel(); label.setWordWrap(True); label.setObjectName("CoachStep")
            self.box.addWidget(label); self.steps.append(label)
        self.detail = QLabel("Everything here works offline."); self.detail.setWordWrap(True); self.detail.setObjectName("Subtle")
        self.box.addWidget(self.detail)
        self.box.addStretch(1)
        self.tour_button = QPushButton("Show me how  →"); self.tour_button.setObjectName("CoachAction")
        self.tour_button.clicked.connect(self.open_tutorial); self.box.addWidget(self.tour_button)
        self.set_module("")

    def set_module(self, title):
        if getattr(self, "tutorial_mode", False): return
        clean = title.replace("&&", "&")
        steps = MODULE_HELP.get(clean, GUIDES[self.key][3])
        self.kicker.setText(clean.upper() if clean else "A LITTLE GUIDANCE")
        for n, (label, text) in enumerate(zip(self.steps, steps), 1): label.setText(f"{n:02d}   {text}")

    def open_tutorial(self):
        win = self.screen.window()
        if hasattr(win, "open_tutorial"): win.open_tutorial(self.key)


class ModuleDeck(QWidget):
    """Visible module cards control the existing tab widget and keep its API."""
    def __init__(self, tabs, coach):
        super().__init__(); self.setObjectName("WorkspaceCanvas")
        box = QVBoxLayout(self); box.setContentsMargins(0, 0, 0, 0); box.setSpacing(12)
        tabs.tabBar().hide(); tabs.setDocumentMode(True)
        grid = QGridLayout(); grid.setSpacing(8); group = QButtonGroup(self)
        self.buttons = []
        count = tabs.count(); cols = 3 if count > 4 else max(1, count)
        for i in range(count):
            name = tabs.tabText(i).replace("&&", "&")
            button = QPushButton(f"{i+1:02d}   {name.replace('&', '&&')}"); button.setObjectName("ModuleCard")
            button.setCheckable(True); button.setMinimumHeight(48); button.setAccessibleName(f"Open {name} module")
            button.clicked.connect(lambda checked=False, index=i: tabs.setCurrentIndex(index))
            group.addButton(button); self.buttons.append(button); grid.addWidget(button, i // cols, i % cols)
        box.addLayout(grid); box.addWidget(tabs, 1)
        def select(index):
            if 0 <= index < len(self.buttons):
                self.buttons[index].setChecked(True); coach.set_module(tabs.tabText(index))
        tabs.currentChanged.connect(select); select(tabs.currentIndex())


def install_workspace(screen, key):
    """Apply one composition to every screen without changing screen identity."""
    if key not in GUIDES or hasattr(screen, "coach"): return
    root = screen.layout()
    if root is None: return
    items = []
    while root.count():
        stretch = root.stretch(0)
        items.append((root.takeAt(0), stretch))
    root.setContentsMargins(22, 18, 22, 18); root.setSpacing(12)
    kicker, title, intro, _ = GUIDES[key]
    head = QWidget(); head.setObjectName("WorkspaceHeader"); hl = QVBoxLayout(head)
    hl.setContentsMargins(0, 0, 0, 0); hl.setSpacing(5)
    tag = QLabel(kicker); tag.setObjectName("Kicker"); hl.addWidget(tag)
    heading = QLabel(title); heading.setWordWrap(True); heading.setObjectName("WorkspaceTitle"); hl.addWidget(heading)
    sub = QLabel(intro); sub.setWordWrap(True); sub.setObjectName("Subtle"); hl.addWidget(sub)
    root.addWidget(head)
    row = QHBoxLayout(); row.setSpacing(18)
    canvas = QWidget(); canvas.setObjectName("WorkspaceCanvas"); body = QVBoxLayout(canvas)
    body.setContentsMargins(0, 0, 0, 0); body.setSpacing(12)
    coach = CoachPanel(screen, key); screen.coach = coach
    if key == "dashboard":
        # Home already has a personal greeting and one editorial hero.
        head.hide()
    if key == "session":
        screen.title.setObjectName("CoachTitle")
        screen.skill_label.setWordWrap(True)
        screen.stat.setWordWrap(True)
    if key == "part_writing":
        # Solver feedback belongs beside the score, not beneath the document.
        coach.detail.hide()
        coach.box.insertWidget(coach.box.count() - 2, screen.diagnostics, 1)
        screen.diagnostics.setMinimumHeight(130)
        screen.editor_tabs.currentChanged.connect(
            lambda index: coach.set_module(screen.editor_tabs.tabText(index)))
        editor_parent_layout = screen.editor_tabs.parentWidget().layout()
        editor_parent_layout.removeWidget(screen.editor_tabs)
        editor_parent_layout.insertWidget(0, ModuleDeck(screen.editor_tabs, coach), 1)
    # Hide only redundant introductory labels, preserving live labels inside layouts.
    for item, stretch in items:
        widget = item.widget()
        if isinstance(widget, QLabel) and widget.objectName() in ("H1", "Kicker", "Subtle"):
            widget.setParent(screen); widget.hide(); continue
        if isinstance(widget, QTabWidget):
            if key == "part_writing":
                body.addWidget(widget, 1)
            else:
                body.addWidget(ModuleDeck(widget, coach), 1)
        elif item.layout() is not None:
            nested = item.layout()
            nested.setParent(None)
            body.addLayout(nested, stretch)
        elif widget is not None:
            body.addWidget(widget, stretch)
        else:
            body.addItem(item)
    canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    row.addWidget(canvas, 1)
    coach_scroll = QScrollArea(); coach_scroll.setWidgetResizable(True); coach_scroll.setWidget(coach)
    coach_scroll.setMinimumWidth(228); coach_scroll.setMaximumWidth(272)
    coach_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    row.addWidget(coach_scroll)
    root.addLayout(row, 1)
    screen.workspace_canvas = canvas
    screen.workspace_header = head
    screen.coach_scroll = coach_scroll
