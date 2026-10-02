"""Durable customer cases and Diwan approval records.

This is the governance bridge between customer intake and human authorization.
Creating a case never approves an action and never sends an external message.
"""

from __future__ import annotations

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
        """)
        self.db.commit()

    def create_case(self, lead_id: int) -> int:
        cur = self.db.execute(
            "INSERT INTO cases(lead_id,status,created_at) VALUES(?,?,?)",
            (lead_id, "OPEN", _now()),
        )
        self.db.commit()
        return int(cur.lastrowid)

    def get_case(self, case_id: int) -> dict[str, Any]:
        row = self.db.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
        if row is None:
            raise KeyError(case_id)
        return dict(row)

    def request_approval(self, case_id: int) -> int:
        if self.get_case(case_id)["status"] not in {"OPEN", "APPROVAL_REQUIRED"}:
            raise ValueError("case_not_open")
        cur = self.db.execute(
            "INSERT INTO approvals(case_id,status) VALUES(?,?)",
            (case_id, "PENDING"),
        )
        self.db.execute(
            "UPDATE cases SET status='APPROVAL_REQUIRED' WHERE id=?", (case_id,)
        )
        self.db.commit()
        return int(cur.lastrowid)

    def decide(self, approval_id: int, actor: str, approved: bool, note: str = "") -> dict[str, Any]:
        row = self.db.execute(
            "SELECT * FROM approvals WHERE id=?", (approval_id,)
        ).fetchone()
        if row is None:
            raise KeyError(approval_id)
        if row["status"] != "PENDING":
            raise ValueError("approval_already_decided")
        status = "APPROVED" if approved else "REJECTED"
        self.db.execute(
            "UPDATE approvals SET status=?,actor=?,note=?,decided_at=? WHERE id=?",
            (status, actor, note, _now(), approval_id),
        )
        self.db.execute(
            "UPDATE cases SET status=? WHERE id=?",
            ("APPROVED" if approved else "REJECTED", row["case_id"]),
        )
        self.db.commit()
        result = self.db.execute(
            "SELECT * FROM approvals WHERE id=?", (approval_id,)
        ).fetchone()
        return dict(result)
