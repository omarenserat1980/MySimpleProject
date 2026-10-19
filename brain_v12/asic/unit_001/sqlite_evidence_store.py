"""Append-only SQLite memory for reproducible Brain experiment evidence.

Stores what was actually tested and when, without treating CI/simulation evidence
as proof of physical ASIC hardware, accepted pool shares, or realized revenue.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_DB = Path(".brain") / "experiment_memory.sqlite3"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ExperimentMemory:
    def __init__(self, db_path: str | Path = DEFAULT_DB):
        self.db_path = Path(db_path).expanduser()

    def connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=10000")
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    @contextmanager
    def connection(self):
        """Commit/rollback transactions and always close the SQLite handle."""
        conn = self.connect()
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def init(self) -> None:
        with self.connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS experiment_events (
                    event_id TEXT PRIMARY KEY,
                    occurred_at_utc TEXT NOT NULL,
                    project TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    environment_json TEXT NOT NULL,
                    measurements_json TEXT NOT NULL,
                    evidence_json TEXT NOT NULL,
                    limitations_json TEXT NOT NULL,
                    created_at_utc TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_experiment_subject_time "
                         "ON experiment_events(subject, occurred_at_utc DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_experiment_type_time "
                         "ON experiment_events(event_type, occurred_at_utc DESC)")

    def record(self, event: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(event, dict):
            raise ValueError("event must be a JSON object")
        for key in ("project", "subject", "event_type", "status"):
            if not isinstance(event.get(key), str) or not event[key].strip():
                raise ValueError(f"{key} must be a non-empty string")
        event_id = str(event.get("event_id") or uuid.uuid4())
        occurred = str(event.get("occurred_at_utc") or utc_now())
        created = utc_now()
        environment = event.get("environment") or {}
        measurements = event.get("measurements") or {}
        evidence = event.get("evidence") or []
        limitations = event.get("limitations") or []
        for key, value in (("environment", environment), ("measurements", measurements),
                           ("evidence", evidence), ("limitations", limitations)):
            if not isinstance(value, (dict, list)):
                raise ValueError(f"{key} must be an object or array")
        # Deliberately reject likely credentials before persistence.
        serialized = json.dumps({
            "environment": environment, "measurements": measurements,
            "evidence": evidence, "limitations": limitations
        }, ensure_ascii=False).lower()
        forbidden = ("password", "access_token", "refresh_token", "private_key",
                     "api_key", "secret", "authorization")
        if any(term in serialized for term in forbidden):
            raise ValueError("event contains a secret-like field or value; refusing persistence")
        with self.connection() as conn:
            conn.execute("""
                INSERT INTO experiment_events (
                    event_id, occurred_at_utc, project, subject, event_type, status,
                    environment_json, measurements_json, evidence_json, limitations_json,
                    created_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (event_id, occurred, event["project"], event["subject"],
                  event["event_type"], event["status"],
                  json.dumps(environment, ensure_ascii=False, sort_keys=True),
                  json.dumps(measurements, ensure_ascii=False, sort_keys=True),
                  json.dumps(evidence, ensure_ascii=False, sort_keys=True),
                  json.dumps(limitations, ensure_ascii=False, sort_keys=True), created))
        return self.get(event_id)

    def get(self, event_id: str) -> dict[str, Any] | None:
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM experiment_events WHERE event_id=?",
                               (event_id,)).fetchone()
        return self._decode(row) if row else None

    def list_events(self, subject: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 1000))
        with self.connection() as conn:
            if subject:
                rows = conn.execute(
                    "SELECT * FROM experiment_events WHERE subject=? "
                    "ORDER BY occurred_at_utc DESC LIMIT ?", (subject, limit)).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM experiment_events ORDER BY occurred_at_utc DESC LIMIT ?",
                    (limit,)).fetchall()
        return [self._decode(row) for row in rows]

    def health(self) -> dict[str, Any]:
        with self.connection() as conn:
            count = conn.execute("SELECT COUNT(*) FROM experiment_events").fetchone()[0]
            version = conn.execute("SELECT sqlite_version()").fetchone()[0]
        return {"status": "SQLITE_READY", "record_count": count,
                "sqlite_version": version, "db_path": str(self.db_path)}

    @staticmethod
    def _decode(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "event_id": row["event_id"], "occurred_at_utc": row["occurred_at_utc"],
            "project": row["project"], "subject": row["subject"],
            "event_type": row["event_type"], "status": row["status"],
            "environment": json.loads(row["environment_json"]),
            "measurements": json.loads(row["measurements_json"]),
            "evidence": json.loads(row["evidence_json"]),
            "limitations": json.loads(row["limitations_json"]),
            "created_at_utc": row["created_at_utc"],
        }
