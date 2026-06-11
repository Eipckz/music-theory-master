"""Centralized error logging and crash-safety helpers.

The GUI must never die on a recoverable error (a single bad exercise, an audio
glitch). PyQt aborts the process when a Python exception escapes a slot, so we
(1) guard slot bodies with :func:`guard`, and (2) install a logging excepthook
as a backstop. Logging uses only the standard library - no network, no
serialization - to honour the offline/no-forbidden-imports contract."""

from __future__ import annotations

import functools
import inspect
import logging
import sys
import traceback
from logging.handlers import RotatingFileHandler
from typing import Callable, Optional

from .paths import log_path

_LOGGER: Optional[logging.Logger] = None
_NOTIFIER: Optional[Callable[[str, str], None]] = None


def get_logger() -> logging.Logger:
    global _LOGGER
    if _LOGGER is not None:
        return _LOGGER
    lg = logging.getLogger("music_theory")
    lg.setLevel(logging.INFO)
    if not lg.handlers:
        try:
            handler = RotatingFileHandler(
                str(log_path()), maxBytes=512 * 1024, backupCount=2, encoding="utf-8"
            )
            handler.setFormatter(
                logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
            )
            lg.addHandler(handler)
        except Exception:  # noqa: BLE001 - logging must never break the app
            lg.addHandler(logging.NullHandler())
    _LOGGER = lg
    return lg


def log_exception(context: str = "") -> None:
    """Record the active exception's traceback without raising."""
    try:
        get_logger().error("%s\n%s", context, traceback.format_exc())
    except Exception:  # noqa: BLE001
        pass


def set_notifier(fn: Optional[Callable[[str, str], None]]) -> None:
    """Register a UI callback ``fn(title, message)`` for surfaced errors."""
    global _NOTIFIER
    _NOTIFIER = fn


def notify(title: str, message: str) -> None:
    if _NOTIFIER is not None:
        try:
            _NOTIFIER(title, message)
        except Exception:  # noqa: BLE001
            pass


def install_excepthook() -> None:
    """Install a logging excepthook so unexpected errors are recorded (and, when
    possible, surfaced) instead of silently closing the window."""

    def _hook(exc_type, exc, tb) -> None:
        try:
            get_logger().error("Unhandled exception", exc_info=(exc_type, exc, tb))
        except Exception:  # noqa: BLE001
            pass
        notify("Something went wrong",
               "An unexpected error occurred but the app kept running. "
               "Details were written to the log.")

    sys.excepthook = _hook


def guard(context: str = ""):
    """Decorator: run a (UI slot) method, logging and swallowing exceptions so a
    recoverable failure can never crash the process.

    Qt signals pass arguments to their slots (e.g. ``QPushButton.clicked`` emits
    a ``checked`` bool). Because this wrapper is variadic, PyQt forwards those
    extra arguments even when the underlying slot does not declare them, which
    would otherwise raise ``TypeError``. We therefore drop any surplus positional
    arguments the wrapped function cannot accept, mirroring how PyQt adapts a
    plain (non-decorated) slot to a signal's arity."""

    def deco(fn: Callable) -> Callable:
        try:
            params = list(inspect.signature(fn).parameters.values())
            accepts_varargs = any(p.kind == p.VAR_POSITIONAL for p in params)
            max_positional = sum(
                1 for p in params
                if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
            )
        except (TypeError, ValueError):  # builtins / unintrospectable callables
            accepts_varargs, max_positional = True, 0

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            if not accepts_varargs and len(args) > max_positional:
                args = args[:max_positional]
            try:
                return fn(*args, **kwargs)
            except Exception:  # noqa: BLE001 - intentional safety net
                log_exception(context or getattr(fn, "__qualname__", "guard"))
                notify("Action interrupted",
                       "That step hit an unexpected problem and was skipped. "
                       "You can keep going.")
                return None
        return wrapper

    return deco
