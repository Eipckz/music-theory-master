"""Celebration moments: a confetti overlay for level-ups / mastery / daily
goals, and a small progress-bar animation helper.

Design constraints:
* lightweight (QPainter particles, no media files, no new dependencies)
* short (under ~1.2 s of motion) and dismissible with a click or Esc
* honors the ``reduce_motion`` setting: shows the same message card with no
  particles and no animation
* purely cosmetic: any failure here must never break the session flow, so the
  public entry points are exception-guarded.
"""

from __future__ import annotations

import math
import random

from PyQt6.QtCore import QPointF, QPropertyAnimation, QRectF, Qt, QTimer
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget

from . import theme

_FRAME_MS = 16
_BURST_MS = 1100          # particle lifetime
_HOLD_MS = 2400           # how long the card stays up after the burst

# per-kind header so milestones feel distinct from each other
_KIND_HEADERS = {
    "level_up": "LEVEL UP",
    "mastery": "SKILL MASTERED",
    "daily_goal": "DAILY GOAL",
    "lesson": "LESSON COMPLETE",
}
_KIND_ICONS = {
    "level_up": "🎉",
    "mastery": "⭐",
    "daily_goal": "✅",
    "lesson": "🎵",
}


class CelebrationOverlay(QWidget):
    """Transparent full-window overlay: confetti burst + message card."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName("Celebration")
        self.hide()
        self._particles: list[dict] = []
        self._active = False
        self._elapsed = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.dismiss)

        self._card = QWidget(self)
        self._card.setObjectName("Card")
        lay = QVBoxLayout(self._card)
        lay.setContentsMargins(28, 20, 28, 20)
        lay.setSpacing(6)
        self._kicker = QLabel("")
        self._kicker.setObjectName("Kicker")
        self._kicker.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._title = QLabel("")
        self._title.setObjectName("H2")
        self._title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._title.setWordWrap(True)
        self._body = QLabel("")
        self._body.setObjectName("BodyLg")
        self._body.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._body.setWordWrap(True)
        self._hint = QLabel("Click anywhere to continue")
        self._hint.setObjectName("Subtle")
        self._hint.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        for w in (self._kicker, self._title, self._body, self._hint):
            lay.addWidget(w)

    # -- public ------------------------------------------------------------
    def celebrate(self, title: str, message: str, *, kind: str = "level_up",
                  reduce_motion: bool = False) -> None:
        """Show the moment. Never raises (cosmetics must not break a session)."""
        try:
            self._show(title, message, kind=kind, reduce_motion=reduce_motion)
        except Exception:  # noqa: BLE001
            self.hide()

    def dismiss(self) -> None:
        self._timer.stop()
        self._hide_timer.stop()
        self._particles = []
        self._active = False
        self.hide()

    @property
    def active(self) -> bool:
        # explicit flag, not isVisible(): a hidden parent (headless tests)
        # must not make a live celebration look dismissed
        return self._active

    # -- internals -----------------------------------------------------------
    def _show(self, title: str, message: str, *, kind: str, reduce_motion: bool) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        self.setGeometry(parent.rect())
        icon = _KIND_ICONS.get(kind, "🎉")
        self._kicker.setText(_KIND_HEADERS.get(kind, "MILESTONE"))
        self._title.setText(f"{icon}  {title}")
        self._body.setText(message)
        self._body.setVisible(bool(message))
        self.setAccessibleDescription(f"{self._kicker.text()}: {title}. {message}")
        self._layout_card()

        self._elapsed = 0
        if reduce_motion:
            self._particles = []
        else:
            self._particles = self._spawn_particles()
            self._timer.start(_FRAME_MS)
        self._active = True
        self.show()
        self.raise_()
        self.setFocus(Qt.FocusReason.PopupFocusReason)
        self._hide_timer.start(_BURST_MS + _HOLD_MS)

    def _layout_card(self) -> None:
        self._card.adjustSize()
        w = min(max(self._card.width(), 360), int(self.width() * 0.8))
        self._card.resize(w, self._card.heightForWidth(w) if self._card.heightForWidth(w) > 0
                          else self._card.height())
        self._card.move((self.width() - self._card.width()) // 2,
                        (self.height() - self._card.height()) // 2)

    def _spawn_particles(self) -> list[dict]:
        rng = random.Random()
        cx, cy = self.width() / 2, self.height() / 2
        colors = [theme.ACCENT, theme.GOOD, theme.WARN, "#e25575", "#7c4dff"]
        out = []
        for _ in range(110):
            ang = rng.uniform(0, 2 * math.pi)
            speed = rng.uniform(4.0, 13.0)
            out.append({
                "x": cx, "y": cy,
                "vx": math.cos(ang) * speed,
                "vy": math.sin(ang) * speed - 4.0,
                "size": rng.uniform(4.0, 9.0),
                "spin": rng.uniform(-0.3, 0.3),
                "rot": rng.uniform(0, math.pi),
                "color": QColor(rng.choice(colors)),
            })
        return out

    def hideEvent(self, event) -> None:  # noqa: N802 - Qt override
        # never leave a 16 ms repaint timer running on a hidden overlay
        self._timer.stop()
        self._hide_timer.stop()
        super().hideEvent(event)

    def _tick(self) -> None:
        if not self._active:
            self._timer.stop()
            return
        self._elapsed += _FRAME_MS
        if self._elapsed >= _BURST_MS:
            self._timer.stop()
            self._particles = []
        else:
            for p in self._particles:
                p["x"] += p["vx"]
                p["y"] += p["vy"]
                p["vy"] += 0.45          # gravity
                p["vx"] *= 0.99
                p["rot"] += p["spin"]
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802 - Qt override
        if not self._particles:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        fade = max(0.0, 1.0 - self._elapsed / _BURST_MS)
        for part in self._particles:
            c = QColor(part["color"])
            c.setAlphaF(fade)
            p.setBrush(c)
            p.setPen(Qt.PenStyle.NoPen)
            p.save()
            p.translate(QPointF(part["x"], part["y"]))
            p.rotate(math.degrees(part["rot"]))
            s = part["size"]
            p.drawRect(QRectF(-s / 2, -s / 4, s, s / 2))
            p.restore()
        p.end()

    def mousePressEvent(self, _event) -> None:  # noqa: N802 - Qt override
        self.dismiss()

    def keyPressEvent(self, event) -> None:  # noqa: N802 - Qt override
        if event.key() in (Qt.Key.Key_Escape, Qt.Key.Key_Return, Qt.Key.Key_Space):
            self.dismiss()
        else:
            super().keyPressEvent(event)


def animate_bar(bar: QProgressBar, value: int, *, reduce_motion: bool = False,
                msec: int = 450) -> None:
    """Slide a progress bar to ``value`` (or jump straight there)."""
    value = max(bar.minimum(), min(bar.maximum(), int(value)))
    if reduce_motion or not bar.isVisible() or bar.value() == value:
        bar.setValue(value)
        return
    anim = QPropertyAnimation(bar, b"value", bar)
    anim.setDuration(msec)
    anim.setStartValue(bar.value())
    anim.setEndValue(value)
    anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
