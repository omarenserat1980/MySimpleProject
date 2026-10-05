from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Callable


class SQLiteStateStore:
    """Durable key/value state with atomic JSON snapshots."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS state (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        self._conn.commit()

    def set(self, key: str, value: Any) -> None:
        if not key:
            raise ValueError("state key is required")
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":"))
        with self._conn:
            self._conn.execute(
                "INSERT INTO state(key,value) VALUES(?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, encoded),
            )

    def get(self, key: str, default: Any = None) -> Any:
        row = self._conn.execute("SELECT value FROM state WHERE key=?", (key,)).fetchone()
        return default if row is None else json.loads(row[0])

    def atomic_update(
        self,
        key: str,
        updater: Callable[[Any], tuple[bool, Any]],
        default: Any = None,
    ) -> tuple[bool, Any]:
        """Run a read/decision/write cycle under one SQLite write transaction."""
        if not key:
            raise ValueError("state key is required")
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            row = self._conn.execute("SELECT value FROM state WHERE key=?", (key,)).fetchone()
            current = default if row is None else json.loads(row[0])
            changed, value = updater(current)
            if changed:
                encoded = json.dumps(value, sort_keys=True, separators=(",", ":"))
                self._conn.execute(
                    "INSERT INTO state(key,value) VALUES(?,?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (key, encoded),
                )
            self._conn.commit()
            return changed, value
        except Exception:
            self._conn.rollback()
            raise

    def snapshot(self) -> dict[str, Any]:
        rows = self._conn.execute("SELECT key,value FROM state ORDER BY key").fetchall()
        return {key: json.loads(value) for key, value in rows}

    def restore(self, snapshot: dict[str, Any]) -> None:
        if not isinstance(snapshot, dict):
            raise TypeError("snapshot must be a dict")
        with self._conn:
            self._conn.execute("DELETE FROM state")
            for key, value in snapshot.items():
                if not key:
                    raise ValueError("state key is required")
                self._conn.execute(
                    "INSERT INTO state(key,value) VALUES(?,?)",
                    (key, json.dumps(value, sort_keys=True, separators=(",", ":"))),
                )

    def is_ready(self) -> bool:
        try:
            self._conn.execute("SELECT 1").fetchone()
            return True
        except sqlite3.Error:
            return False

    def close(self) -> None:
        self._conn.close()
