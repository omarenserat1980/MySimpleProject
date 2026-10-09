"""Local-first Brain Home Server task bridge.

Run locally with:
    uvicorn brain_v12.home_server:app --host 127.0.0.1 --port 8765

Task/control endpoints fail closed unless BRAIN_CONTROL_KEY is configured.
This service queues only named, allowlisted task types; it never executes
arbitrary shell commands. SQLite is used for durable queue state and recovery.
"""
from __future__ import annotations

import hmac
import json
import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

APP_VERSION = "0.1.0"
ALLOWED_TASKS = {"python_version", "platform", "brain_self_test", "status"}


def _db_path() -> Path:
    configured = os.getenv("BRAIN_HOME_SERVER_DB", "").strip()
    return Path(configured).expanduser() if configured else Path.home() / ".brain" / "home-server.sqlite3"


class TaskInput(BaseModel):
    task: str
    params: dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=0, ge=-10, le=10)
    required_capabilities: list[str] = Field(default_factory=list, max_length=20)
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=200)


class ClaimInput(BaseModel):
    worker_id: str = Field(min_length=1, max_length=120)
    capabilities: list[str] = Field(default_factory=list, max_length=50)
    lease_seconds: int = Field(default=60, ge=10, le=900)


class ReportInput(BaseModel):
    worker_id: str = Field(min_length=1, max_length=120)
    ok: bool
    result: dict[str, Any] = Field(default_factory=dict)
    error: str = Field(default="", max_length=4000)


class HomeServerStore:
    def __init__(self, path: Path | None = None):
        self.path = path or _db_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.init()

    @contextmanager
    def connect(self):
        db = sqlite3.connect(str(self.path), timeout=10, isolation_level=None)
        db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA busy_timeout=10000")
            db.execute("PRAGMA journal_mode=WAL")
            yield db
        finally:
            db.close()

    def init(self) -> None:
        with self.connect() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS home_tasks (
                    task_id TEXT PRIMARY KEY,
                    task TEXT NOT NULL,
                    params_json TEXT NOT NULL,
                    priority INTEGER NOT NULL DEFAULT 0,
                    required_capabilities_json TEXT NOT NULL DEFAULT '[]',
                    status TEXT NOT NULL,
                    idempotency_key TEXT UNIQUE,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    worker_id TEXT,
                    lease_until REAL,
                    result_json TEXT,
                    error TEXT NOT NULL DEFAULT ''
                )
            """)
            columns = {row["name"] for row in db.execute("PRAGMA table_info(home_tasks)")}
            if "priority" not in columns:
                db.execute("ALTER TABLE home_tasks ADD COLUMN priority INTEGER NOT NULL DEFAULT 0")
            if "required_capabilities_json" not in columns:
                db.execute("ALTER TABLE home_tasks ADD COLUMN required_capabilities_json TEXT NOT NULL DEFAULT '[]'")
            db.execute("CREATE INDEX IF NOT EXISTS idx_home_tasks_status_created ON home_tasks(status, priority DESC, created_at)")

    @staticmethod
    def _item(row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        item["params"] = json.loads(item.pop("params_json"))
        item["required_capabilities"] = json.loads(item.pop("required_capabilities_json", "[]"))
        item["result"] = json.loads(item.pop("result_json")) if item.get("result_json") else None
        item.pop("result_json", None)
        return item

    def enqueue(self, task: str, params: dict[str, Any], idempotency_key: str | None, priority: int = 0, required_capabilities: list[str] | None = None) -> dict[str, Any]:
        if task not in ALLOWED_TASKS:
            raise ValueError("TASK_NOT_ALLOWED")
        if not -10 <= priority <= 10:
            raise ValueError("PRIORITY_OUT_OF_RANGE")
        capabilities = sorted(set(required_capabilities or []))
        if any(not cap or len(cap) > 80 for cap in capabilities):
            raise ValueError("INVALID_CAPABILITY")
        now = time.time()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                if idempotency_key:
                    existing = db.execute("SELECT * FROM home_tasks WHERE idempotency_key=?", (idempotency_key,)).fetchone()
                    if existing:
                        db.execute("COMMIT")
                        return self._item(existing)
                task_id = "home-" + uuid4().hex
                db.execute(
                    """INSERT INTO home_tasks
                    (task_id, task, params_json, status, idempotency_key, created_at, updated_at)
                    VALUES (?, ?, ?, 'QUEUED', ?, ?, ?)""",
                    (task_id, task, json.dumps(params, separators=(",", ":"), sort_keys=True), idempotency_key, now, now),
                )
                row = db.execute("SELECT * FROM home_tasks WHERE task_id=?", (task_id,)).fetchone()
                db.execute("COMMIT")
                return self._item(row)
            except Exception:
                db.execute("ROLLBACK")
                raise

    def status(self) -> dict[str, Any]:
        now = time.time()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute(
                "UPDATE home_tasks SET status='QUEUED', worker_id=NULL, lease_until=NULL, updated_at=? WHERE status='CLAIMED' AND lease_until < ?",
                (now, now),
            )
            counts = {row["status"]: row["n"] for row in db.execute("SELECT status, COUNT(*) AS n FROM home_tasks GROUP BY status")}
            db.execute("COMMIT")
        return {
            "ok": True,
            "service": "brain-home-server",
            "version": APP_VERSION,
            "database": "sqlite",
            "database_path": str(self.path),
            "queue": {name: counts.get(name, 0) for name in ("QUEUED", "CLAIMED", "COMPLETED", "FAILED")},
        }

    def list_tasks(self, limit: int = 50) -> list[dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute("SELECT * FROM home_tasks ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [self._item(row) for row in rows]

    def claim(self, worker_id: str, lease_seconds: int, capabilities: list[str] | None = None) -> dict[str, Any]:
        now = time.time()
        worker_capabilities = set(capabilities or [])
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                db.execute(
                    "UPDATE home_tasks SET status='QUEUED', worker_id=NULL, lease_until=NULL, updated_at=? WHERE status='CLAIMED' AND lease_until < ?",
                    (now, now),
                )
                queued = db.execute("SELECT * FROM home_tasks WHERE status='QUEUED' ORDER BY priority DESC, created_at ASC").fetchall()
                row = next((candidate for candidate in queued if set(json.loads(candidate["required_capabilities_json"])).issubset(worker_capabilities)), None)
                if row is None:
                    db.execute("COMMIT")
                    return {"ok": True, "status": "IDLE", "task": None}
                lease_until = now + lease_seconds
                db.execute(
                    "UPDATE home_tasks SET status='CLAIMED', worker_id=?, lease_until=?, attempts=attempts+1, updated_at=? WHERE task_id=? AND status='QUEUED'",
                    (worker_id, lease_until, now, row["task_id"]),
                )
                claimed = db.execute("SELECT * FROM home_tasks WHERE task_id=?", (row["task_id"],)).fetchone()
                db.execute("COMMIT")
                return {"ok": True, "status": "TASK_AVAILABLE", "task": self._item(claimed)}
            except Exception:
                db.execute("ROLLBACK")
                raise

    def report(self, task_id: str, worker_id: str, ok: bool, result: dict[str, Any], error: str) -> dict[str, Any]:
        now = time.time()
        final_status = "COMPLETED" if ok else "FAILED"
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM home_tasks WHERE task_id=?", (task_id,)).fetchone()
            if row is None:
                db.execute("ROLLBACK")
                raise KeyError("TASK_NOT_FOUND")
            if row["status"] != "CLAIMED" or row["worker_id"] != worker_id:
                db.execute("ROLLBACK")
                raise PermissionError("WORKER_LEASE_MISMATCH")
            db.execute(
                "UPDATE home_tasks SET status=?, result_json=?, error=?, updated_at=?, lease_until=NULL WHERE task_id=?",
                (final_status, json.dumps(result, separators=(",", ":"), sort_keys=True), error, now, task_id),
            )
            updated = db.execute("SELECT * FROM home_tasks WHERE task_id=?", (task_id,)).fetchone()
            db.execute("COMMIT")
            return {"ok": True, "task": self._item(updated)}


store: HomeServerStore | None = None


def get_store() -> HomeServerStore:
    global store
    if store is None:
        store = HomeServerStore()
    return store


app = FastAPI(title="Brain Home Server", version=APP_VERSION)


def _authorize(authorization: str | None, *, worker: bool = False) -> None:
    if worker:
        # Device/worker credentials are deliberately separate from admin control.
        expected = (
            os.getenv("BRAIN_AGENT_KEY", "").strip()
            or os.getenv("BRAIN_EMULATOR_KEY", "").strip()
            or os.getenv("BRAIN_EMULATOR_AGENT_KEY", "").strip()
            or os.getenv("TERMUX_AGENT_KEY", "").strip()
        )
        missing_code = "HOME_SERVER_WORKER_AUTH_NOT_CONFIGURED"
        required_code = "WORKER_AUTH_REQUIRED"
    else:
        expected = os.getenv("BRAIN_CONTROL_KEY", "").strip()
        missing_code = "HOME_SERVER_CONTROL_NOT_CONFIGURED"
        required_code = "CONTROL_AUTH_REQUIRED"
    if not expected:
        raise HTTPException(status_code=503, detail=missing_code)
    supplied = (authorization or "").strip()
    if not hmac.compare_digest(supplied, "Bearer " + expected):
        raise HTTPException(status_code=401, detail=required_code)


@app.get("/health")
def health():
    return {"ok": True, "service": "brain-home-server", "version": APP_VERSION}


@app.get("/api/home-server/status")
def home_server_status():
    result = get_store().status()
    result["control_auth_configured"] = bool(os.getenv("BRAIN_CONTROL_KEY", "").strip())
    return result


@app.get("/api/home-server/tasks")
def list_tasks(limit: int = 50, authorization: str | None = Header(default=None)):
    _authorize(authorization)
    return {"ok": True, "tasks": get_store().list_tasks(max(1, min(limit, 200)))}


@app.post("/api/home-server/tasks")
def create_task(body: TaskInput, authorization: str | None = Header(default=None)):
    _authorize(authorization)
    try:
        return {"ok": True, "task": get_store().enqueue(body.task, body.params, body.idempotency_key, body.priority, body.required_capabilities)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/home-server/claim")
def claim_task(body: ClaimInput, authorization: str | None = Header(default=None)):
    _authorize(authorization, worker=True)
    return get_store().claim(body.worker_id, body.lease_seconds, body.capabilities)


@app.post("/api/home-server/tasks/{task_id}/report")
def report_task(task_id: str, body: ReportInput, authorization: str | None = Header(default=None)):
    _authorize(authorization, worker=True)
    try:
        return get_store().report(task_id, body.worker_id, body.ok, body.result, body.error)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
