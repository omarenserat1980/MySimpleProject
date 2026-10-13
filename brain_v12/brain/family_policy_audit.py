"""SQLite-backed tamper-evident audit chain for family policy decisions.

The chain detects accidental or unsophisticated row edits; without a protected
external signing key it is not a cryptographic signature or proof against an
attacker who can rewrite the whole database.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from contextlib import closing
from pathlib import Path
from typing import Any

GENESIS_HASH = "0" * 64


class FamilyPolicyAudit:
    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path).expanduser().resolve()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS family_policy_audit (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    event_json TEXT NOT NULL,
                    previous_hash TEXT NOT NULL,
                    event_hash TEXT NOT NULL UNIQUE
                )"""
            )
            db.execute(
                """CREATE TABLE IF NOT EXISTS family_approval_consumption (
                    consent_reference TEXT PRIMARY KEY,
                    action TEXT NOT NULL,
                    task_fingerprint TEXT NOT NULL,
                    consumed_at REAL NOT NULL
                )"""
            )

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.database_path, timeout=10.0, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout=10000")
        return db

    @staticmethod
    def _hash(timestamp: float, event_json: str, previous_hash: str) -> str:
        material = json.dumps(
            {"timestamp": timestamp, "event_json": event_json, "previous_hash": previous_hash},
            sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        )
        return hashlib.sha256(material.encode("utf-8")).hexdigest()

    def append(self, event: dict[str, Any]) -> dict[str, Any]:
        event_json = json.dumps(event, sort_keys=True, separators=(",", ":"),
                                ensure_ascii=False, allow_nan=False)
        timestamp = time.time()
        with closing(self._connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                row = db.execute(
                    "SELECT event_hash FROM family_policy_audit ORDER BY sequence DESC LIMIT 1"
                ).fetchone()
                previous_hash = row["event_hash"] if row else GENESIS_HASH
                event_hash = self._hash(timestamp, event_json, previous_hash)
                cursor = db.execute(
                    """INSERT INTO family_policy_audit
                       (timestamp, event_json, previous_hash, event_hash)
                       VALUES (?, ?, ?, ?)""",
                    (timestamp, event_json, previous_hash, event_hash),
                )
                db.execute("COMMIT")
                return {"sequence": int(cursor.lastrowid), "event_hash": event_hash,
                        "previous_hash": previous_hash, "timestamp": timestamp}
            except Exception:
                db.execute("ROLLBACK")
                raise

    def consume_approval(self, consent_reference: str, action: str,
                         task_fingerprint: str) -> bool:
        """Consume a consent reference once; transactionally blocks replay."""
        if not consent_reference or not action or not task_fingerprint:
            return False
        with closing(self._connect()) as db:
            try:
                db.execute(
                    """INSERT INTO family_approval_consumption
                       (consent_reference, action, task_fingerprint, consumed_at)
                       VALUES (?, ?, ?, ?)""",
                    (consent_reference, action, task_fingerprint, time.time()),
                )
                return True
            except sqlite3.IntegrityError:
                return False

    def verify(self) -> dict[str, Any]:
        with closing(self._connect()) as db:
            rows = db.execute(
                "SELECT sequence, timestamp, event_json, previous_hash, event_hash "
                "FROM family_policy_audit ORDER BY sequence"
            ).fetchall()
        previous_hash = GENESIS_HASH
        for expected_sequence, row in enumerate(rows, start=1):
            if row["sequence"] != expected_sequence:
                return {"ok": False, "status": "AUDIT_SEQUENCE_GAP",
                        "failed_sequence": row["sequence"], "checked": expected_sequence - 1}
            if row["previous_hash"] != previous_hash:
                return {"ok": False, "status": "AUDIT_CHAIN_LINK_MISMATCH",
                        "failed_sequence": row["sequence"], "checked": expected_sequence - 1}
            actual_hash = self._hash(row["timestamp"], row["event_json"], previous_hash)
            if actual_hash != row["event_hash"]:
                return {"ok": False, "status": "AUDIT_EVENT_HASH_MISMATCH",
                        "failed_sequence": row["sequence"], "checked": expected_sequence - 1}
            previous_hash = actual_hash
        return {"ok": True, "status": "AUDIT_CHAIN_VALID", "checked": len(rows),
                "last_hash": previous_hash, "signature": "NONE_HASH_CHAIN_ONLY"}
