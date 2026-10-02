"""Lead-to-case service with explicit governance and audit events."""

from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class CustomerCaseStore:
    def __init__(self, path: str | Path = "data/customer_cases.db") -> None:
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS cases (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          lead_id INTEGER NOT NULL,
          status TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS approvals (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          case_id INTEGER NOT NULL,
          status TEXT NOT NULL,
          actor TEXT,
          note TEXT,
          decided_at TEXT
        );
        CREATE TABLE IF NOT EXISTS case_events (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          case_id INTEGER NOT NULL,
          event_type TEXT NOT NULL,
          actor TEXT NOT NULL,
          payload_hash TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        """)
        self.db.commit()

    def _event(self, case_id: int, event_type: str, actor: str, payload: str = "") -> None:
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        self.db.execute(
            "INSERT INTO case_events(case_id,event_type,actor,payload_hash,created_at) VALUES(?,?,?,?,?)",
            (case_id, event_type, actor, digest, _now()),
        )

    def create_case(self, lead_id: int) -> int:
        cur = self.db.execute(
            "INSERT INTO cases(lead_id,status,created_at) VALUES(?,?,?)",
            (lead_id, "OPEN", _now()),
        )
        case_id = int(cur.lastrowid)
        self._event(case_id, "CASE_CREATED", "system", str(lead_id))
        self.db.commit()
        return case_id

    def get_case(self, case_id: int) -> dict[str, Any]:
        row = self.db.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
        if row is None:
            raise KeyError(case_id)
        return dict(row)

    def events(self, case_id: int) -> list[dict[str, Any]]:
        rows = self.db.execute("SELECT * FROM case_events WHERE case_id=? ORDER BY id", (case_id,)).fetchall()
        return [dict(r) for r in rows]

    def request_approval(self, case_id: int, actor: str = "system") -> int:
        if self.get_case(case_id)["status"] not in {"OPEN", "APPROVAL_REQUIRED"}:
            raise ValueError("case_not_open")
        cur = self.db.execute("INSERT INTO approvals(case_id,status) VALUES(?,?)", (case_id, "PENDING"))
        self.db.execute("UPDATE cases SET status='APPROVAL_REQUIRED' WHERE id=?", (case_id,))
        self._event(case_id, "APPROVAL_REQUESTED", actor, str(cur.lastrowid))
        self.db.commit()
        return int(cur.lastrowid)

    def decide(self, approval_id: int, actor: str, approved: bool, note: str = "") -> dict[str, Any]:
        row = self.db.execute("SELECT * FROM approvals WHERE id=?", (approval_id,)).fetchone()
        if row is None:
            raise KeyError(approval_id)
        if row["status"] != "PENDING":
            raise ValueError("approval_already_decided")
        status = "APPROVED" if approved else "REJECTED"
        self.db.execute("UPDATE approvals SET status=?,actor=?,note=?,decided_at=? WHERE id=?",
                        (status, actor, note, _now(), approval_id))
        self.db.execute("UPDATE cases SET status=? WHERE id=?", (status, row["case_id"]))
        self._event(row["case_id"], "APPROVAL_DECIDED", actor, f"{approval_id}|{status}|{note}")
        self.db.commit()
        result = self.db.execute("SELECT * FROM approvals WHERE id=?", (approval_id,)).fetchone()
        return dict(result)
