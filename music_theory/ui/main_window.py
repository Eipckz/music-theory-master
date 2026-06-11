"""Main application window: sidebar navigation over a stack of screens."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QButtonGroup, QHBoxLayout, QLabel, QPushButton, QStackedWidget, QVBoxLayout, QWidget,
)

from .. import __app_name__
from ..errors import guard, set_notifier
from .screens.about import AboutScreen
from .screens.dashboard import DashboardScreen
from .screens.piano_workspace import PianoWorkspaceScreen
from .screens.placement import PlacementScreen
from .screens.practice import PracticeScreen
from .screens.session import SessionScreen
from .screens.settings import SettingsScreen
from .screens.stats import StatsScreen

from PyQt6.QtWidgets import QMainWindow

_NAV = [
    ("Home", "dashboard"),
    ("Learn", "session"),
    ("Practice", "practice"),
    ("Dictation", "dictation"),
    ("Piano", "piano"),
    ("Progress", "stats"),
    ("Placement", "placement"),
    ("Settings", "settings"),
    ("About", "about"),
]


class MainWindow(QMainWindow):
    def __init__(self, ctx, parent=None) -> None:
        super().__init__(parent)
        self.ctx = ctx
        self.setWindowTitle(__app_name__)
        self.resize(1140, 740)
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
        self._add("piano", PianoWorkspaceScreen(ctx))
        self._add("stats", StatsScreen(ctx))
        self._add("placement", PlacementScreen(ctx))
        self._add("settings", SettingsScreen(ctx))
        self._add("about", AboutScreen(ctx))

        for name, screen in self.screens.items():
            if hasattr(screen, "navigate"):
                screen.navigate = self.go_to

        sidebar = self._build_sidebar()
        layout.addWidget(sidebar)
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(central)

        self._toast = _Toast(self)
        set_notifier(lambda title, msg: self.toast(f"{title}: {msg}", kind="warning"))

        start = "placement" if not self.ctx.settings.get("placement_done", False) else "dashboard"
        self.go_to(start)

    def toast(self, message: str, *, kind: str = "info", msec: int = 2600) -> None:
        """Show a brief, non-modal notification (level-ups, achievements, errors)."""
        self._toast.show_message(message, kind=kind, msec=msec)

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().resizeEvent(event)
        if hasattr(self, "_toast"):
            self._toast.reposition()

    def _add(self, name: str, widget: QWidget) -> None:
        self.screens[name] = widget
        self.stack.addWidget(widget)

    def _build_sidebar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("Sidebar")
        bar.setFixedWidth(196)
        lay = QVBoxLayout(bar)
        lay.setContentsMargins(10, 14, 10, 14)
        lay.setSpacing(4)
        brand = QLabel("\u266B  Music Theory\nMaster")
        brand.setObjectName("Brand")
        lay.addWidget(brand)
        lay.addSpacing(8)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self._nav_buttons: dict[str, QPushButton] = {}
        for label, name in _NAV:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.clicked.connect(lambda _=False, n=name: self.go_to(n))
            lay.addWidget(btn)
            self.nav_group.addButton(btn)
            self._nav_buttons[name] = btn
        lay.addStretch(1)
        return bar

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


_TOAST_COLORS = {
    "info": "#2f3b52", "success": "#2f7d4f", "warning": "#8a5a1f", "error": "#8a2f2f",
}


class _Toast(QLabel):
    """Lightweight, auto-dismissing overlay banner."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setVisible(False)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

    def show_message(self, message: str, *, kind: str = "info", msec: int = 2600) -> None:
        bg = _TOAST_COLORS.get(kind, _TOAST_COLORS["info"])
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
