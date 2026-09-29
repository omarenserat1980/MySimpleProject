from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
import sqlite3
from . import service
from .service import BrainGitError

STATUSES = {"queued", "running", "success", "failed", "cancelled"}
TERMINAL = {"success", "failed", "cancelled"}


@dataclass(frozen=True)
class WorkflowRun:
    id: int
    namespace: str
    repository: str
    workflow: str
    ref: str
    status: str
    created_at: str
    attempt_count: int = 0
    worker_id: str | None = None
    heartbeat_at: str | None = None


def _init():
    service.initialize()
    with sqlite3.connect(service.DB) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS workflow_runs(
          id INTEGER PRIMARY KEY AUTOINCREMENT, namespace TEXT, repository TEXT,
          workflow TEXT, ref TEXT, status TEXT, created_at TEXT, completed_at TEXT,
          attempt_count INTEGER NOT NULL DEFAULT 0, worker_id TEXT, heartbeat_at TEXT)""")
        columns = {row[1] for row in db.execute("PRAGMA table_info(workflow_runs)")}
        migrations = {
            "attempt_count": "ALTER TABLE workflow_runs ADD COLUMN attempt_count INTEGER NOT NULL DEFAULT 0",
            "worker_id": "ALTER TABLE workflow_runs ADD COLUMN worker_id TEXT",
            "heartbeat_at": "ALTER TABLE workflow_runs ADD COLUMN heartbeat_at TEXT",
        }
        for name, sql in migrations.items():
            if name not in columns:
                db.execute(sql)
        db.commit()


def dispatch(namespace: str, repository: str, workflow: str, ref: str = "main") -> WorkflowRun:
    if not all(isinstance(x, str) and x.strip() for x in (namespace, repository, workflow, ref)):
        raise BrainGitError("workflow dispatch fields must be non-empty strings")
    _init()
    now = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(service.DB) as db:
        cur = db.execute(
            "INSERT INTO workflow_runs(namespace,repository,workflow,ref,status,created_at) VALUES(?,?,?,?,?,?)",
            (namespace, repository, workflow, ref, "queued", now),
        )
        db.commit()
        return get_run(cur.lastrowid)


def claim_next(worker_id: str, max_attempts: int = 3) -> dict | None:
    if not isinstance(worker_id, str) or not worker_id.strip():
        raise BrainGitError("worker_id must be a non-empty string")
    if max_attempts < 1:
        raise BrainGitError("max_attempts must be positive")
    _init()
    now = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(service.DB, timeout=30, isolation_level="IMMEDIATE") as db:
        row = db.execute(
            "SELECT id FROM workflow_runs WHERE status='queued' AND attempt_count < ? ORDER BY id LIMIT 1",
            (max_attempts,),
        ).fetchone()
        if not row:
            return None
        run_id = row[0]
        cur = db.execute(
            """UPDATE workflow_runs
               SET status='running', worker_id=?, heartbeat_at=?, attempt_count=attempt_count+1
               WHERE id=? AND status='queued' AND attempt_count < ?""",
            (worker_id, now, run_id, max_attempts),
        )
        if cur.rowcount != 1:
            return None
        db.commit()
    return get_run(run_id)


def recover_stale(timeout_seconds: int = 900, max_attempts: int = 3) -> int:
    if timeout_seconds < 1 or max_attempts < 1:
        raise BrainGitError("timeout_seconds and max_attempts must be positive")
    _init()
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=timeout_seconds)
    with sqlite3.connect(service.DB) as db:
        rows = db.execute(
            "SELECT id, attempt_count FROM workflow_runs WHERE status='running' AND heartbeat_at IS NOT NULL AND heartbeat_at < ?",
            (cutoff.isoformat(),),
        ).fetchall()
        recovered = 0
        for run_id, attempts in rows:
            if attempts < max_attempts:
                db.execute(
                    "UPDATE workflow_runs SET status='queued', worker_id=NULL, heartbeat_at=NULL WHERE id=? AND status='running'",
                    (run_id,),
                )
            else:
                db.execute(
                    "UPDATE workflow_runs SET status='failed', worker_id=NULL, heartbeat_at=NULL, completed_at=? WHERE id=? AND status='running'",
                    (datetime.now(timezone.utc).isoformat(), run_id),
                )
            recovered += 1
        db.commit()
    return recovered


def heartbeat(run_id: int, worker_id: str) -> None:
    _init()
    now = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(service.DB) as db:
        cur = db.execute(
            "UPDATE workflow_runs SET heartbeat_at=? WHERE id=? AND status='running' AND worker_id=?",
            (now, run_id, worker_id),
        )
        if cur.rowcount != 1:
            raise BrainGitError("workflow run is not owned by worker")
        db.commit()


def retry(run_id: int) -> None:
    _init()
    with sqlite3.connect(service.DB) as db:
        row = db.execute("SELECT status, attempt_count FROM workflow_runs WHERE id=?", (run_id,)).fetchone()
        if not row:
            raise BrainGitError("workflow run not found")
        if row[0] != "failed":
            raise BrainGitError("only failed runs can be retried")
        db.execute(
            "UPDATE workflow_runs SET status='queued', worker_id=NULL, heartbeat_at=NULL, completed_at=NULL, attempt_count=0 WHERE id=?",
            (run_id,),
        )
        db.commit()


def set_status(run_id: int, status: str, worker_id: str | None = None) -> None:
    if status not in STATUSES:
        raise BrainGitError("invalid workflow status")
    _init()
    with sqlite3.connect(service.DB) as db:
        row = db.execute("SELECT status, worker_id FROM workflow_runs WHERE id=?", (run_id,)).fetchone()
        if not row:
            raise BrainGitError("workflow run not found")
        current, owner = row
        if current in TERMINAL:
            raise BrainGitError("workflow run is already terminal")
        if current == "running" and owner and worker_id != owner:
            raise BrainGitError("workflow run is owned by another worker")
        if status == "running" and current != "queued":
            raise BrainGitError("only queued runs can enter running state")
        if status in TERMINAL and current == "queued" and status != "cancelled":
            raise BrainGitError("queued runs can only be cancelled")
        completed = datetime.now(timezone.utc).isoformat() if status in TERMINAL else None
        heartbeat_at = None if status != "running" else datetime.now(timezone.utc).isoformat()
        db.execute(
            "UPDATE workflow_runs SET status=?, completed_at=?, heartbeat_at=?, worker_id=? WHERE id=?",
            (status, completed, heartbeat_at, owner if status == "running" else None, run_id),
        )
        db.commit()


def cancel(run_id: int) -> None:
    set_status(run_id, "cancelled")


def get_run(run_id: int) -> dict:
    _init()
    with sqlite3.connect(service.DB) as db:
        row = db.execute(
            """SELECT id,namespace,repository,workflow,ref,status,created_at,
                      attempt_count,worker_id,heartbeat_at
               FROM workflow_runs WHERE id=?""",
            (run_id,),
        ).fetchone()
    if not row:
        raise BrainGitError("workflow run not found")
    return asdict(WorkflowRun(*row))
