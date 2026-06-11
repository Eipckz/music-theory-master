"""SQLite-backed progress store.

Security notes:
* Every statement uses bound parameters - no string-interpolated SQL.
* The database lives in the per-user app-data directory; no remote access.
* Stored JSON blobs are produced by us and re-validated on read; we never
  eval/pickle untrusted content.
"""

from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Iterator, Optional

from ..paths import database_path

SCHEMA_VERSION = 1

_SCHEMA = """
CREATE TABLE IF NOT EXISTS profile (
    id              INTEGER PRIMARY KEY CHECK (id = 1),
    name            TEXT    NOT NULL DEFAULT 'Learner',
    created_at      REAL    NOT NULL,
    total_xp        INTEGER NOT NULL DEFAULT 0,
    streak_days     INTEGER NOT NULL DEFAULT 0,
    last_active_day TEXT    NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS mastery (
    skill_id     TEXT    PRIMARY KEY,
    rating       REAL    NOT NULL DEFAULT 1000.0,  -- Elo-style ability
    mastery_prob REAL    NOT NULL DEFAULT 0.10,    -- BKT-lite P(known)
    stability    REAL    NOT NULL DEFAULT 0.0,     -- FSRS memory stability (days)
    difficulty   REAL    NOT NULL DEFAULT 5.0,     -- FSRS item difficulty 1..10
    reps         INTEGER NOT NULL DEFAULT 0,
    lapses       INTEGER NOT NULL DEFAULT 0,
    n_attempts   INTEGER NOT NULL DEFAULT 0,
    n_correct    INTEGER NOT NULL DEFAULT 0,
    last_seen    REAL    NOT NULL DEFAULT 0,
    due_at       REAL    NOT NULL DEFAULT 0,
    unlocked     INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS attempts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ts           REAL    NOT NULL,
    skill_id     TEXT    NOT NULL,
    domain       TEXT    NOT NULL DEFAULT '',
    exercise_type TEXT   NOT NULL DEFAULT '',
    difficulty   REAL    NOT NULL DEFAULT 0,
    correct      INTEGER NOT NULL DEFAULT 0,
    response_ms  INTEGER NOT NULL DEFAULT 0,
    params_json  TEXT    NOT NULL DEFAULT '{}',
    source       TEXT    NOT NULL DEFAULT 'course'  -- course | practice | placement
);
CREATE INDEX IF NOT EXISTS idx_attempts_skill ON attempts(skill_id);
CREATE INDEX IF NOT EXISTS idx_attempts_ts ON attempts(ts);

CREATE TABLE IF NOT EXISTS placement_results (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    ts        REAL    NOT NULL,
    domain    TEXT    NOT NULL,
    theta     REAL    NOT NULL,
    ci        REAL    NOT NULL,
    level     TEXT    NOT NULL,
    n_items   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS achievements (
    key         TEXT PRIMARY KEY,
    unlocked_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS kv (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


class Database:
    """Thin, fully parameterized wrapper around the progress SQLite file."""

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = Path(path) if path else database_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._migrate()
        self._ensure_profile()

    # -- schema -----------------------------------------------------------
    def _migrate(self) -> None:
        with self.conn:
            self.conn.executescript(_SCHEMA)
            cur = self.conn.execute("PRAGMA user_version")
            version = cur.fetchone()[0]
            if version < SCHEMA_VERSION:
                # Future migrations branch on `version` here.
                self.conn.execute(f"PRAGMA user_version = {int(SCHEMA_VERSION)}")

    def _ensure_profile(self) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT OR IGNORE INTO profile (id, name, created_at) VALUES (1, ?, ?)",
                ("Learner", time.time()),
            )

    def reset_progress(self) -> None:
        """Wipe all learning progress, keeping the profile row but resetting its
        counters. Used by the Settings 'Reset progress' action."""
        with self.conn:
            self.conn.execute("DELETE FROM mastery")
            self.conn.execute("DELETE FROM attempts")
            self.conn.execute("DELETE FROM placement_results")
            self.conn.execute("DELETE FROM achievements")
            self.conn.execute("DELETE FROM kv")
            self.conn.execute(
                "UPDATE profile SET total_xp = 0, streak_days = 0, "
                "last_active_day = '' WHERE id = 1"
            )

    @contextmanager
    def tx(self) -> Iterator[sqlite3.Connection]:
        with self.conn:
            yield self.conn

    def close(self) -> None:
        try:
            self.conn.close()
        except sqlite3.Error:
            pass

    # -- profile ----------------------------------------------------------
    def get_profile(self) -> dict[str, Any]:
        row = self.conn.execute("SELECT * FROM profile WHERE id = 1").fetchone()
        return dict(row) if row else {}

    def update_profile(self, **fields: Any) -> None:
        allowed = {"name", "total_xp", "streak_days", "last_active_day"}
        sets = {k: v for k, v in fields.items() if k in allowed}
        if not sets:
            return
        cols = ", ".join(f"{k} = ?" for k in sets)
        with self.conn:
            self.conn.execute(
                f"UPDATE profile SET {cols} WHERE id = 1", tuple(sets.values())
            )

    def add_xp(self, amount: int) -> int:
        with self.conn:
            self.conn.execute(
                "UPDATE profile SET total_xp = total_xp + ? WHERE id = 1", (int(amount),)
            )
        self._bump_daily_xp(int(amount))
        return int(self.get_profile().get("total_xp", 0))

    def _bump_daily_xp(self, amount: int) -> None:
        key = "xp.day." + time.strftime("%Y-%m-%d")
        self.kv_set(key, int(self.kv_get(key, 0) or 0) + amount)

    def today_xp(self) -> int:
        return int(self.kv_get("xp.day." + time.strftime("%Y-%m-%d"), 0) or 0)

    # -- mastery ----------------------------------------------------------
    def get_mastery(self, skill_id: str) -> Optional[dict[str, Any]]:
        row = self.conn.execute(
            "SELECT * FROM mastery WHERE skill_id = ?", (skill_id,)
        ).fetchone()
        return dict(row) if row else None

    def all_mastery(self) -> dict[str, dict[str, Any]]:
        rows = self.conn.execute("SELECT * FROM mastery").fetchall()
        return {r["skill_id"]: dict(r) for r in rows}

    def upsert_mastery(self, skill_id: str, **fields: Any) -> None:
        existing = self.get_mastery(skill_id)
        cols = {
            "rating", "mastery_prob", "stability", "difficulty", "reps",
            "lapses", "n_attempts", "n_correct", "last_seen", "due_at", "unlocked",
        }
        data = {k: v for k, v in fields.items() if k in cols}
        with self.conn:
            if existing is None:
                data["skill_id"] = skill_id
                keys = ", ".join(data.keys())
                ph = ", ".join("?" for _ in data)
                self.conn.execute(
                    f"INSERT INTO mastery ({keys}) VALUES ({ph})", tuple(data.values())
                )
            elif data:
                sets = ", ".join(f"{k} = ?" for k in data)
                self.conn.execute(
                    f"UPDATE mastery SET {sets} WHERE skill_id = ?",
                    (*data.values(), skill_id),
                )

    def set_unlocked(self, skill_ids: Iterable[str], unlocked: bool = True) -> None:
        with self.conn:
            for sid in skill_ids:
                self.upsert_mastery(sid, unlocked=1 if unlocked else 0)

    # -- attempts ---------------------------------------------------------
    def log_attempt(
        self,
        skill_id: str,
        correct: bool,
        *,
        domain: str = "",
        exercise_type: str = "",
        difficulty: float = 0.0,
        response_ms: int = 0,
        params: Optional[dict[str, Any]] = None,
        source: str = "course",
    ) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO attempts "
                "(ts, skill_id, domain, exercise_type, difficulty, correct, "
                " response_ms, params_json, source) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    time.time(), skill_id, domain, exercise_type, float(difficulty),
                    1 if correct else 0, int(response_ms),
                    json.dumps(params or {}), source,
                ),
            )

    def recent_attempts(self, limit: int = 100) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM attempts ORDER BY ts DESC LIMIT ?", (int(limit),)
        ).fetchall()
        return [dict(r) for r in rows]

    def attempt_counts(self) -> tuple[int, int]:
        row = self.conn.execute(
            "SELECT COUNT(*) AS n, COALESCE(SUM(correct), 0) AS c FROM attempts"
        ).fetchone()
        return int(row["n"]), int(row["c"])

    def daily_activity(self, days: int = 30) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT CAST(strftime('%s', date(ts, 'unixepoch', 'localtime')) AS INTEGER) AS day, "
            "COUNT(*) AS n, COALESCE(SUM(correct),0) AS c "
            "FROM attempts GROUP BY day ORDER BY day DESC LIMIT ?",
            (int(days),),
        ).fetchall()
        return [dict(r) for r in rows]

    # -- placement --------------------------------------------------------
    def save_placement(
        self, domain: str, theta: float, ci: float, level: str, n_items: int
    ) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO placement_results (ts, domain, theta, ci, level, n_items) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (time.time(), domain, float(theta), float(ci), level, int(n_items)),
            )

    def latest_placement(self) -> dict[str, dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT domain, theta, ci, level, ts FROM placement_results "
            "ORDER BY ts DESC"
        ).fetchall()
        out: dict[str, dict[str, Any]] = {}
        for r in rows:
            if r["domain"] not in out:
                out[r["domain"]] = dict(r)
        return out

    # -- achievements -----------------------------------------------------
    def unlock_achievement(self, key: str) -> bool:
        existing = self.conn.execute(
            "SELECT 1 FROM achievements WHERE key = ?", (key,)
        ).fetchone()
        if existing:
            return False
        with self.conn:
            self.conn.execute(
                "INSERT INTO achievements (key, unlocked_at) VALUES (?, ?)",
                (key, time.time()),
            )
        return True

    def achievements(self) -> list[str]:
        rows = self.conn.execute(
            "SELECT key FROM achievements ORDER BY unlocked_at"
        ).fetchall()
        return [r["key"] for r in rows]

    def achievements_with_dates(self) -> dict[str, float]:
        """key -> unlock timestamp, for the achievements gallery."""
        rows = self.conn.execute(
            "SELECT key, unlocked_at FROM achievements ORDER BY unlocked_at"
        ).fetchall()
        return {r["key"]: float(r["unlocked_at"]) for r in rows}

    # -- key/value --------------------------------------------------------
    def kv_get(self, key: str, default: Any = None) -> Any:
        row = self.conn.execute("SELECT value FROM kv WHERE key = ?", (key,)).fetchone()
        if row is None:
            return default
        try:
            return json.loads(row["value"])
        except (json.JSONDecodeError, TypeError):
            return default

    def kv_set(self, key: str, value: Any) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO kv (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, json.dumps(value)),
            )
