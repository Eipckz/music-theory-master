"""Main application window: sidebar navigation over a stack of screens."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QButtonGroup, QFrame, QHBoxLayout, QLabel, QPushButton, QStackedWidget,
    QVBoxLayout, QWidget, QScrollArea,
)

from .. import __app_name__
from ..errors import guard, set_notifier
from . import theme
from .workspace import install_workspace, icon_for
from .celebration import CelebrationOverlay
from .screens.about import AboutScreen
from .screens.achievements import AchievementsScreen
from .screens.dashboard import DashboardScreen
from .screens.piano_workspace import PianoWorkspaceScreen
from .screens.part_writing import PartWritingScreen
from .screens.placement import PlacementScreen
from .screens.practice import PracticeScreen
from .screens.practice_tools import PracticeToolsScreen
from .screens.studio import StudioScreen
from .screens.reference import ReferenceScreen
from .screens.session import SessionScreen
from .screens.settings import SettingsScreen
from .screens.stats import StatsScreen
from .screens.tutorial import TutorialScreen

from PyQt6.QtWidgets import QMainWindow

_NAV = [
    ("Home", "dashboard"),
    ("Learn", "session"),
    ("Practice", "practice"),
    ("Part Writing", "part_writing"),
    ("Dictation", "dictation"),
    ("Piano", "piano"),
    ("Reference", "reference"),
    ("Tools", "tools"),
    ("Studio", "studio"),
    ("Tutorial", "tutorial"),
    ("Progress", "stats"),
    ("Awards", "achievements"),
    ("Placement", "placement"),
    ("Settings", "settings"),
    ("About", "about"),
]


class MainWindow(QMainWindow):
    def __init__(self, ctx, parent=None) -> None:
        super().__init__(parent)
        self.ctx = ctx
        self.setWindowTitle(__app_name__)
        self.resize(1320, 900)
        self.setMinimumSize(940, 620)

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.stack = QStackedWidget()
        self.screens: dict[str, QWidget] = {}
        self._add("dashboard", DashboardScreen(ctx))
        self.session = SessionScreen(ctx)
        self._add("session", self.session)
        self.practice = PracticeScreen(ctx)
        self._add("practice", self.practice)
        self._add("part_writing", PartWritingScreen(ctx))
        self._add("piano", PianoWorkspaceScreen(ctx))
        self._add("reference", ReferenceScreen(ctx))
        self._add("tools", PracticeToolsScreen(ctx))
        self._add("studio", StudioScreen(ctx))
        self._add("stats", StatsScreen(ctx))
        self._add("achievements", AchievementsScreen(ctx))
        self._add("placement", PlacementScreen(ctx))
        self._add("settings", SettingsScreen(ctx))
        self._add("about", AboutScreen(ctx))
        self._add("tutorial", TutorialScreen(ctx))

        for name, screen in self.screens.items():
            if hasattr(screen, "navigate"):
                screen.navigate = self.go_to

        sidebar = self._build_sidebar()
        layout.addWidget(sidebar)
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(central)

        self._toast = _Toast(self)
        self._celebration = CelebrationOverlay(self)
        set_notifier(lambda title, msg: self.toast(f"{title}: {msg}", kind="warning"))

        start = "placement" if not self.ctx.settings.get("placement_done", False) else "dashboard"
        if not self.ctx.settings.get("onboarding_seen", False):
            start = "tutorial"
        self.go_to(start)

    def open_tutorial(self, module="part_writing"):
        self.screens["tutorial"].show_guide(module)
        self.go_to("tutorial")

    def closeEvent(self, event):
        self.ctx.engine.stop()
        self.screens["tutorial"].close()
        self.screens["part_writing"].close()
        super().closeEvent(event)

    def toast(self, message: str, *, kind: str = "info", msec: int = 2600) -> None:
        """Show a brief, non-modal notification (achievements, errors)."""
        self._toast.show_message(message, kind=kind, msec=msec)

    @guard("MainWindow.celebrate")
    def celebrate(self, title: str, message: str, *, kind: str = "level_up") -> None:
        """Full celebration moment (confetti + card) for the big milestones."""
        reduce = bool(self.ctx.settings.get("reduce_motion", False))
        self._celebration.celebrate(title, message, kind=kind, reduce_motion=reduce)

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().resizeEvent(event)
        if hasattr(self, "_toast"):
            self._toast.reposition()
        if hasattr(self, "_celebration") and self._celebration.isVisible():
            self._celebration.setGeometry(self.rect())

    def _add(self, name: str, widget: QWidget) -> None:
        install_workspace(widget, name)
        self.screens[name] = widget
        self.stack.addWidget(widget)

    def _build_sidebar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("Sidebar")
        bar.setMinimumWidth(168)
        lay = QVBoxLayout(bar)
        lay.setContentsMargins(10, 12, 10, 12)
        lay.setSpacing(2)
        from ..paths import resources_dir
        mark = QLabel()
        mark.setPixmap(QPixmap(str(resources_dir() / "icons" / "conservatory.svg")).scaled(
            42, 42, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        mark.setFixedSize(38, 42)
        brand_row = QHBoxLayout(); brand_row.setContentsMargins(5, 0, 0, 0)
        brand_row.addWidget(mark)
        brand = QLabel("Music Theory\nMaster")
        brand.setWordWrap(True)
        brand.setObjectName("Brand")
        brand.setStyleSheet('font-family: "Georgia"; font-size: 16px; padding: 0px;')
        brand_row.addWidget(brand, 1); lay.addLayout(brand_row)
        lay.addSpacing(2)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self._nav_buttons: dict[str, QPushButton] = {}
        for label, name in _NAV:
            if name in ("dashboard", "part_writing", "stats", "settings"):
                section = QLabel({"dashboard": "YOUR PRACTICE", "part_writing": "THE WORKSPACE",
                                  "stats": "YOUR JOURNEY", "settings": "PREFERENCES"}[name])
                section.setObjectName("NavSection")
                lay.addWidget(section)
            btn = QPushButton(label)
            btn.setIcon(icon_for(name))
            btn.setStyleSheet("text-align: left; padding: 5px 10px; min-height: 18px;")
            btn.setCheckable(True)
            btn.clicked.connect(lambda _=False, n=name: self.go_to(n))
            lay.addWidget(btn)
            self.nav_group.addButton(btn)
            self._nav_buttons[name] = btn
        lay.addStretch(1)
        scroll = QScrollArea()
        scroll.setObjectName("SidebarScroll")
        scroll.setWidgetResizable(True)
        scroll.setFixedWidth(184)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(bar)
        return scroll

    @guard("MainWindow.go_to")
    def go_to(self, name: str) -> None:
        target = {"dictation": "practice", "review": "session"}.get(name, name)
        screen = self.screens.get(target)
        if screen is None:
            return
        self.stack.setCurrentWidget(screen)
        btn = self._nav_buttons.get(name) or self._nav_buttons.get(target)
        if btn is not None:
            btn.setChecked(True)
        if name == "dictation":
            self.practice.preset(domain="aural", etype="melodic_dictation")
        elif name == "review":
            self.session.preset_weak()
        elif hasattr(screen, "on_show"):
            screen.on_show()
        # move keyboard focus into the new screen so keyboard/screen-reader
        # users don't stay stranded on the sidebar
        screen.setFocus(Qt.FocusReason.OtherFocusReason)


class _Toast(QLabel):
    """Lightweight, auto-dismissing overlay banner."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setAccessibleName("Notification")
        self.setVisible(False)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

    def show_message(self, message: str, *, kind: str = "info", msec: int = 2600) -> None:
        bg = theme.TOAST_COLORS.get(kind, theme.TOAST_COLORS["info"])
        # warnings/errors stay up longer: 2.6 s is too brief for slow readers
        if kind in ("warning", "error") and msec <= 2600:
            msec = 6000
        self.setStyleSheet(
            f"background:{bg}; color:#ffffff; font-size:14px; font-weight:600; "
            "border-radius:10px; padding:10px 16px;"
        )
        self.setText(message)
        self.adjustSize()
        self.reposition()
        self.setVisible(True)
        self.raise_()
        self._timer.start(max(800, msec))

    def reposition(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        max_w = int(parent.width() * 0.6)
        self.setMaximumWidth(max_w)
        self.adjustSize()
        x = (parent.width() - self.width()) // 2
        self.move(max(12, x), 18)
