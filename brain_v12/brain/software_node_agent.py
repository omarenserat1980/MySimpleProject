"""Persistent local task queue and heartbeat agent for a software-only Brain node.

The SQLite queue survives process restarts on the same local filesystem. It is
not a distributed queue and does not imply remote connectivity or real hardware.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import closing
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from .initial_software_node import ALLOWED_TASKS, InitialSoftwareNode, NODE_ID

SCHEMA = "electronic-brain.software-node-agent.v1"
DEFAULT_LEASE_SECONDS = 60.0


class PersistentTaskQueue:
    """SQLite-backed, local durable queue with leases and idempotency keys."""

    def __init__(self, database_path: str | Path, *, lease_seconds: float = DEFAULT_LEASE_SECONDS):
        if lease_seconds <= 0:
            raise ValueError("LEASE_SECONDS_MUST_BE_POSITIVE")
        self.database_path = Path(database_path).expanduser().resolve()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.lease_seconds = float(lease_seconds)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10.0, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=10000")
        return connection

    def _initialize(self) -> None:
        with closing(self._connect()) as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute(
                """CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    idempotency_key TEXT UNIQUE,
                    task_json TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN
                        ('PENDING','RUNNING','COMPLETED','FAILED')),
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    lease_until REAL,
                    lease_token TEXT,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    result_json TEXT
                )"""
            )
            db.execute(
                """CREATE INDEX IF NOT EXISTS idx_brain_tasks_ready
                   ON tasks(status, created_at)"""
            )
            db.execute(
                """CREATE TABLE IF NOT EXISTS node_state (
                    node_id TEXT PRIMARY KEY,
                    heartbeat_sequence INTEGER NOT NULL DEFAULT 0,
                    heartbeat_at REAL,
                    state TEXT NOT NULL DEFAULT 'STOPPED'
                )"""
            )
            db.execute(
                "INSERT OR IGNORE INTO node_state(node_id, state) VALUES (?, 'STOPPED')",
                (NODE_ID,),
            )

    @staticmethod
    def _validate_task(task: dict[str, Any]) -> None:
        if not isinstance(task, dict):
            raise ValueError("INVALID_TASK")
        kind = task.get("type")
        if kind not in ALLOWED_TASKS:
            raise ValueError("TASK_TYPE_NOT_ALLOWED")
        try:
            json.dumps(task, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ValueError("TASK_MUST_BE_JSON_SERIALIZABLE") from exc

    def enqueue(self, task: dict[str, Any], *, idempotency_key: str | None = None) -> dict[str, Any]:
        self._validate_task(task)
        if idempotency_key is not None and (
            not isinstance(idempotency_key, str) or not idempotency_key.strip()
        ):
            raise ValueError("INVALID_IDEMPOTENCY_KEY")
        now = time.time()
        task_id = str(uuid.uuid4())
        payload = json.dumps(task, separators=(",", ":"), allow_nan=False)
        with closing(self._connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                if idempotency_key:
                    existing = db.execute(
                        "SELECT task_id, status FROM tasks WHERE idempotency_key=?",
                        (idempotency_key,),
                    ).fetchone()
                    if existing:
                        db.execute("COMMIT")
                        return {"ok": True, "task_id": existing["task_id"],
                                "status": existing["status"], "deduplicated": True}
                db.execute(
                    """INSERT INTO tasks
                       (task_id, idempotency_key, task_json, status, created_at, updated_at)
                       VALUES (?, ?, ?, 'PENDING', ?, ?)""",
                    (task_id, idempotency_key, payload, now, now),
                )
                db.execute("COMMIT")
            except Exception:
                db.execute("ROLLBACK")
                raise
        return {"ok": True, "task_id": task_id, "status": "PENDING", "deduplicated": False}

    def claim(self) -> dict[str, Any] | None:
        """Claim the oldest task; expired RUNNING leases return to PENDING."""
        now = time.time()
        token = str(uuid.uuid4())
        with closing(self._connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                db.execute(
                    """UPDATE tasks SET status='PENDING', lease_until=NULL, lease_token=NULL,
                              updated_at=?
                       WHERE status='RUNNING' AND lease_until < ?""",
                    (now, now),
                )
                row = db.execute(
                    "SELECT task_id, task_json, attempts FROM tasks "
                    "WHERE status='PENDING' ORDER BY created_at, task_id LIMIT 1"
                ).fetchone()
                if row is None:
                    db.execute("COMMIT")
                    return None
                changed = db.execute(
                    """UPDATE tasks SET status='RUNNING', lease_until=?, lease_token=?,
                              attempts=attempts+1, updated_at=?
                       WHERE task_id=? AND status='PENDING'""",
                    (now + self.lease_seconds, token, now, row["task_id"]),
                ).rowcount
                if changed != 1:
                    db.execute("ROLLBACK")
                    return None
                db.execute("COMMIT")
                return {"task_id": row["task_id"], "task": json.loads(row["task_json"]),
                        "attempt": int(row["attempts"]) + 1, "lease_token": token}
            except Exception:
                db.execute("ROLLBACK")
                raise

    def finish(self, task_id: str, lease_token: str, result: dict[str, Any]) -> bool:
        now = time.time()
        payload = json.dumps(result, separators=(",", ":"), allow_nan=False)
        status = "COMPLETED" if result.get("ok") else "FAILED"
        with closing(self._connect()) as db:
            changed = db.execute(
                """UPDATE tasks SET status=?, result_json=?, updated_at=?,
                          lease_until=NULL, lease_token=NULL
                   WHERE task_id=? AND status='RUNNING' AND lease_token=?""",
                (status, payload, now, task_id, lease_token),
            ).rowcount
        return changed == 1

    def get(self, task_id: str) -> dict[str, Any] | None:
        with closing(self._connect()) as db:
            row = db.execute(
                "SELECT task_id, task_json, status, created_at, updated_at, attempts, result_json "
                "FROM tasks WHERE task_id=?", (task_id,)
            ).fetchone()
        if row is None:
            return None
        return {
            "task_id": row["task_id"], "task": json.loads(row["task_json"]),
            "status": row["status"], "created_at": row["created_at"],
            "updated_at": row["updated_at"], "attempts": row["attempts"],
            "result": json.loads(row["result_json"]) if row["result_json"] else None,
        }

    def counts(self) -> dict[str, int]:
        with closing(self._connect()) as db:
            rows = db.execute("SELECT status, COUNT(*) AS n FROM tasks GROUP BY status").fetchall()
        result = {key: 0 for key in ("PENDING", "RUNNING", "COMPLETED", "FAILED")}
        result.update({row["status"]: int(row["n"]) for row in rows})
        return result

    def record_heartbeat(self, state: str) -> dict[str, Any]:
        now = time.time()
        with closing(self._connect()) as db:
            db.execute(
                """UPDATE node_state SET heartbeat_sequence=heartbeat_sequence+1,
                          heartbeat_at=?, state=? WHERE node_id=?""",
                (now, state, NODE_ID),
            )
            row = db.execute(
                "SELECT heartbeat_sequence, heartbeat_at, state FROM node_state WHERE node_id=?",
                (NODE_ID,),
            ).fetchone()
        return {"node_id": NODE_ID, "sequence": int(row["heartbeat_sequence"]),
                "timestamp": float(row["heartbeat_at"]), "state": row["state"]}

    def heartbeat_status(self) -> dict[str, Any]:
        with closing(self._connect()) as db:
            row = db.execute(
                "SELECT heartbeat_sequence, heartbeat_at, state FROM node_state WHERE node_id=?",
                (NODE_ID,),
            ).fetchone()
        return {"node_id": NODE_ID, "sequence": int(row["heartbeat_sequence"]),
                "timestamp": row["heartbeat_at"], "state": row["state"],
                "storage": "LOCAL_SQLITE"}


class SoftwareNodeAgent:
    """Cooperative local worker with durable tasks and a stoppable heartbeat loop."""

    def __init__(
        self,
        root: str | Path,
        *,
        database_path: str | Path | None = None,
        heartbeat_interval: float = 5.0,
        lease_seconds: float = DEFAULT_LEASE_SECONDS,
    ):
        if heartbeat_interval <= 0:
            raise ValueError("HEARTBEAT_INTERVAL_MUST_BE_POSITIVE")
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        default_db = self.root.parent / f".{self.root.name}-brain-agent.sqlite3"
        self.queue = PersistentTaskQueue(database_path or default_db, lease_seconds=lease_seconds)
        self.node = InitialSoftwareNode(self.root)
        self.heartbeat_interval = float(heartbeat_interval)
        self._stop_event = threading.Event()
        self._heartbeat_thread: threading.Thread | None = None
        self._started = False

    def start(self) -> dict[str, Any]:
        if self._started:
            return self.status()
        self.node.start()
        self._stop_event.clear()
        self._started = True
        self.queue.record_heartbeat("READY_SIMULATED")
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop, name="brain-node-heartbeat", daemon=True
        )
        self._heartbeat_thread.start()
        return self.status()

    def _heartbeat_loop(self) -> None:
        while not self._stop_event.wait(self.heartbeat_interval):
            if self._started:
                self.queue.record_heartbeat("READY_SIMULATED")

    def run_once(self) -> dict[str, Any]:
        if not self._started:
            return {"ok": False, "status": "AGENT_NOT_STARTED", "node_id": NODE_ID}
        claimed = self.queue.claim()
        if claimed is None:
            return {"ok": True, "status": "QUEUE_EMPTY", "node_id": NODE_ID}
        result = self.node.execute(claimed["task"])
        persisted = self.queue.finish(claimed["task_id"], claimed["lease_token"], result)
        return {"ok": persisted and result.get("ok", False),
                "status": "TASK_FINISHED" if persisted else "LEASE_LOST",
                "task_id": claimed["task_id"], "attempt": claimed["attempt"],
                "task_result": result}

    def status(self) -> dict[str, Any]:
        return {
            "ok": self._started,
            "schema": SCHEMA,
            "node_id": NODE_ID,
            "agent_state": "RUNNING_SIMULATED" if self._started else "STOPPED",
            "execution_mode": "SANDBOXED_SOFTWARE_TASKS",
            "heartbeat": self.queue.heartbeat_status(),
            "queue": self.queue.counts(),
            "queue_storage": "LOCAL_SQLITE_DURABLE_ON_THIS_FILESYSTEM",
            "distributed_queue": False,
            "physical_host_contacted": False,
            "network_io_enabled": False,
            "shell_execution_enabled": False,
            "external_resources_created": False,
            "windows_server_2025_boot_verified": False,
        }

    def stop(self, *, timeout: float = 2.0) -> dict[str, Any]:
        self._started = False
        self._stop_event.set()
        thread = self._heartbeat_thread
        if thread is not None:
            thread.join(timeout=max(0.0, timeout))
        self.node.stop()
        self.queue.record_heartbeat("STOPPED")
        self._heartbeat_thread = None
        return self.status()
