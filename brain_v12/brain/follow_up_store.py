"""SQLite-backed persistent follow-up ledger for Electronic Brain.

The ledger is a resumable project handoff, not a source of truth for external
systems. Task statuses must be updated only when evidence has been checked.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATUSES = {"PLANNED", "IN_PROGRESS", "BLOCKED", "PASS", "FAIL", "NOT_PROVEN", "NOT_RUN"}
_LOCK = threading.RLock()

DEFAULT_TASKS = (
    {
        "task_id": "TRACK-001",
        "title": "Auto Clicker prototype",
        "status": "PASS",
        "detail": "PR #971 is merged; safety-policy prototype only, no real Android taps.",
        "next_action": "Review and implement a permission-gated Android adapter with device tests.",
        "evidence": ["https://github.com/omarenserat1980/MySimpleProject/pull/971"],
    },
    {
        "task_id": "TRACK-002",
        "title": "Capability prototypes",
        "status": "PASS",
        "detail": "PR #972 is merged; initial offline/testable prototypes only.",
        "next_action": "Integrate existing canonical modules without duplicating production components.",
        "evidence": ["https://github.com/omarenserat1980/MySimpleProject/pull/972"],
    },
    {
        "task_id": "TRACK-003",
        "title": "Bounded self-healing tests",
        "status": "PASS",
        "detail": "Clean Termux checkout: 8 targeted pytest tests passed; dependency-free self-test reported SELF_TEST=PASS. Test harness only.",
        "next_action": "Run a separately identified production/runtime recovery cycle before changing film metadata.",
        "evidence": [
            "https://github.com/omarenserat1980/MySimpleProject/blob/main/brain_v12/self_healing/test_supervisor_repair_cycle.py",
            "https://github.com/omarenserat1980/MySimpleProject/blob/main/brain_v12/self_healing/self_test.py",
        ],
    },
    {
        "task_id": "TRACK-004",
        "title": "Persist project handoff",
        "status": "PASS",
        "detail": "Markdown tracker merged; SQLite ledger now provides durable task state.",
        "next_action": "Keep the ledger current as verified work changes.",
        "evidence": ["https://github.com/omarenserat1980/MySimpleProject/blob/main/docs/BRAIN_FOLLOW_UP.md"],
    },
    {
        "task_id": "TRACK-005",
        "title": "Follow-up status view",
        "status": "IN_PROGRESS",
        "detail": "SQLite store and API are being added; visual dashboard integration remains separate.",
        "next_action": "Expose read-only status and task listing endpoints; protect all updates with the Brain control key.",
        "evidence": [],
    },
    {
        "task_id": "TRACK-006",
        "title": "Safe mining readiness preflight",
        "status": "PLANNED",
        "detail": "Must remain read-only and must not start mining or contact a pool.",
        "next_action": "Run the existing local/offline compute preflight and record its exact output.",
        "evidence": ["https://github.com/omarenserat1980/MySimpleProject/blob/main/brain_v12/brain/mining_node_api.py"],
    },
    {
        "task_id": "TRACK-007",
        "title": "Real mining and revenue proof",
        "status": "BLOCKED",
        "detail": "Production compute service and native mining backend are not implemented; execution gate is blocked.",
        "next_action": "Do not enable execution until host attestation, pool adapter, accepted-share evidence, payout and cost evidence are verified and explicitly authorized.",
        "evidence": ["https://github.com/omarenserat1980/MySimpleProject/blob/main/brain_v12/brain/mining_node_api.py"],
    },
    {
        "task_id": "TRACK-008",
        "title": "Thin Membrane cloud handoff",
        "status": "BLOCKED",
        "detail": "Live Termux DeviceBridge reports the Realme agent online and authenticated, but Thin Membrane has no approved cloud endpoint or configured device identity; cloud connection, heartbeat and task round-trip are not verified.",
        "next_action": "Configure an approved HTTPS Brain Cloud Hub URL and explicit BRAIN_DEVICE_ID through the authorized deployment environment, then verify TLS connectivity, authenticated heartbeat and a harmless task round-trip. Do not create or print credentials.",
        "evidence": [
            "https://github.com/omarenserat1980/MySimpleProject/blob/main/brain_v12/brain/thin_membrane.py",
            "https://github.com/omarenserat1980/MySimpleProject/blob/main/brain_v12/brain/device_bridge.py",
        ],
    },
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_db_path() -> Path:
    explicit = os.getenv("BRAIN_FOLLOW_UP_DB", "").strip()
    if explicit:
        return Path(explicit).expanduser()
    runtime_home = Path(os.getenv("BRAIN_RUNTIME_HOME", ".brain/runtime")).expanduser()
    return runtime_home / "state" / "follow_up.sqlite3"


class FollowUpStore:
    """Thread-safe SQLite task ledger with an append-only status event history."""

    def __init__(self, path: str | os.PathLike[str] | None = None):
        self.path = Path(path).expanduser() if path is not None else default_db_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path, timeout=10)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA busy_timeout=10000")
        return con

    @contextmanager
    def _connection(self):
        con = self._connect()
        try:
            with con:
                yield con
        finally:
            con.close()

    def _initialize(self) -> None:
        with _LOCK, self._connection() as con:
            con.executescript("""
                CREATE TABLE IF NOT EXISTS follow_up_tasks (
                    task_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    detail TEXT NOT NULL,
                    next_action TEXT NOT NULL,
                    evidence_json TEXT NOT NULL DEFAULT '[]',
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS follow_up_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    previous_status TEXT,
                    new_status TEXT NOT NULL,
                    note TEXT NOT NULL,
                    evidence_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_follow_up_events_task
                    ON follow_up_events(task_id, event_id);
            """)
            for task in DEFAULT_TASKS:
                con.execute(
                    """INSERT OR IGNORE INTO follow_up_tasks
                       (task_id,title,status,detail,next_action,evidence_json,updated_at)
                       VALUES(?,?,?,?,?,?,?)""",
                    (
                        task["task_id"], task["title"], task["status"], task["detail"],
                        task["next_action"], json.dumps(task["evidence"], ensure_ascii=False),
                        utc_now(),
                    ),
                )

    @staticmethod
    def _decode(row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        item = dict(row)
        item["evidence"] = json.loads(item.pop("evidence_json"))
        return item

    def list_tasks(self) -> list[dict[str, Any]]:
        with _LOCK, self._connection() as con:
            rows = con.execute(
                "SELECT * FROM follow_up_tasks ORDER BY "
                "CASE status WHEN 'IN_PROGRESS' THEN 0 WHEN 'BLOCKED' THEN 1 "
                "WHEN 'FAIL' THEN 2 WHEN 'NOT_PROVEN' THEN 3 WHEN 'PLANNED' THEN 4 "
                "WHEN 'NOT_RUN' THEN 5 ELSE 6 END, task_id"
            ).fetchall()
            return [self._decode(row) for row in rows]

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        with _LOCK, self._connect() as con:
            return self._decode(con.execute(
                "SELECT * FROM follow_up_tasks WHERE task_id=?", (task_id,)
            ).fetchone())

    def summary(self) -> dict[str, Any]:
        with _LOCK, self._connect() as con:
            rows = con.execute(
                "SELECT status, COUNT(*) AS count FROM follow_up_tasks GROUP BY status"
            ).fetchall()
            counts = {status: 0 for status in sorted(STATUSES)}
            counts.update({row["status"]: row["count"] for row in rows})
            total = sum(counts.values())
            return {
                "ok": True,
                "schema": "brain-follow-up/v1",
                "storage": "sqlite",
                "database_path": str(self.path),
                "total_tasks": total,
                "counts": counts,
                "active_tasks": counts["IN_PROGRESS"],
                "blocked_tasks": counts["BLOCKED"],
                "last_updated_at": con.execute(
                    "SELECT MAX(updated_at) FROM follow_up_tasks"
                ).fetchone()[0],
            }

    def update_task(
        self,
        task_id: str,
        *,
        status: str,
        note: str,
        evidence: list[str] | None = None,
        next_action: str | None = None,
    ) -> dict[str, Any]:
        if status not in STATUSES:
            raise ValueError("INVALID_STATUS")
        safe_note = str(note).strip()[:2000]
        if not safe_note:
            raise ValueError("UPDATE_NOTE_REQUIRED")
        clean_evidence = [str(value).strip()[:1000] for value in (evidence or []) if str(value).strip()][:20]
        if status == "PASS" and not clean_evidence:
            raise ValueError("PASS_REQUIRES_EVIDENCE")
        now = utc_now()
        with _LOCK, self._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute("SELECT * FROM follow_up_tasks WHERE task_id=?", (task_id,)).fetchone()
            if row is None:
                con.rollback()
                raise KeyError("TASK_NOT_FOUND")
            previous = row["status"]
            existing_evidence = json.loads(row["evidence_json"])
            merged_evidence = clean_evidence if evidence is not None else existing_evidence
            con.execute(
                """UPDATE follow_up_tasks SET status=?, detail=?, next_action=?,
                   evidence_json=?, updated_at=? WHERE task_id=?""",
                (
                    status, safe_note,
                    str(next_action).strip()[:2000] if next_action is not None else row["next_action"],
                    json.dumps(merged_evidence, ensure_ascii=False), now, task_id,
                ),
            )
            con.execute(
                """INSERT INTO follow_up_events
                   (task_id,previous_status,new_status,note,evidence_json,created_at)
                   VALUES(?,?,?,?,?,?)""",
                (task_id, previous, status, safe_note,
                 json.dumps(clean_evidence, ensure_ascii=False), now),
            )
            con.commit()
        return self.get_task(task_id)

    def history(self, task_id: str, limit: int = 50) -> list[dict[str, Any]]:
        with _LOCK, self._connect() as con:
            rows = con.execute(
                """SELECT event_id,task_id,previous_status,new_status,note,
                          evidence_json,created_at FROM follow_up_events
                   WHERE task_id=? ORDER BY event_id DESC LIMIT ?""",
                (task_id, max(1, min(int(limit), 100))),
            ).fetchall()
            result = []
            for row in rows:
                item = dict(row)
                item["evidence"] = json.loads(item.pop("evidence_json"))
                result.append(item)
            return result
