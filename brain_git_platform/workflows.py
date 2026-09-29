from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import sqlite3
from . import service
from .service import BrainGitError


STATUSES = {"queued", "running", "success", "failed", "cancelled"}


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
        if "attempt_count" not in columns:
            db.execute("ALTER TABLE workflow_runs ADD COLUMN attempt_count INTEGER NOT NULL DEFAULT 0")
        if "worker_id" not in columns:
            db.execute("ALTER TABLE workflow_runs ADD COLUMN worker_id TEXT")
        if "heartbeat_at" not in columns:
            db.execute("ALTER TABLE workflow_runs ADD COLUMN heartbeat_at TEXT")
        db.commit()


def dispatch(namespace: str, repository: str, workflow: str, ref: str = "main") -> WorkflowRun:
    _init()
    now = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(service.DB) as db:
        cur = db.execute(
            """INSERT INTO workflow_runs(namespace,repository,workflow,ref,status,created_at)
               VALUES(?,?,?,?,?,?)""",
            (namespace, repository, workflow, ref, "queued", now),
        )
        db.commit()
        return get_run(cur.lastrowid)


def claim_next(worker_id: str) -> dict | None:
    _init()
    now = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(service.DB, timeout=30, isolation_level="IMMEDIATE") as db:
        row = db.execute(
            "SELECT id FROM workflow_runs WHERE status='queued' ORDER BY id LIMIT 1"
        ).fetchone()
        if not row:
            return None
        run_id = row[0]
        cur = db.execute(
            """UPDATE workflow_runs
               SET status='running', worker_id=?, heartbeat_at=?, attempt_count=attempt_count+1
               WHERE id=? AND status='queued'""",
            (worker_id, now, run_id),
        )
        if cur.rowcount != 1:
            return None
        db.commit()
    return get_run(run_id)


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
        cur = db.execute(
            "UPDATE workflow_runs SET status='queued', worker_id=NULL, heartbeat_at=NULL, completed_at=NULL WHERE id=? AND status='failed'",
            (run_id,),
        )
        if cur.rowcount != 1:
            raise BrainGitError("only failed runs can be retried")
        db.commit()


def set_status(run_id: int, status: str) -> None:
    if status not in STATUSES:
        raise BrainGitError("invalid workflow status")
    _init()
    with sqlite3.connect(service.DB) as db:
        cur = db.execute(
            """UPDATE workflow_runs
               SET status=?, completed_at=?, heartbeat_at=CASE WHEN ?='running' THEN heartbeat_at ELSE NULL END
               WHERE id=?""",
            (
                status,
                datetime.now(timezone.utc).isoformat() if status in {"success", "failed", "cancelled"} else None,
                status,
                run_id,
            ),
        )
        if cur.rowcount != 1:
            raise BrainGitError("workflow run not found")
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
