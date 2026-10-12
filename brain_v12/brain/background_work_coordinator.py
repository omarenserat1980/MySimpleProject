"""Durable, bounded, simulation-first background work coordinator.

Jobs are persisted in SQLite and re-queued after process restart. Only safe,
allowlisted simulation tasks are executable here; no shell/device side effects.
"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, Future
from pathlib import Path
from threading import RLock
from typing import Any
from uuid import uuid4
import json, os, sqlite3, time

class BackgroundWorkCoordinator:
    ALLOWED = {"simulation_health", "simulation_inventory", "simulation_readiness"}

    def __init__(self, *, max_workers: int | None = None, max_pending: int = 64,
                 db_path: str | Path | None = None, autostart: bool = True,
                 handlers: dict[str, Any] | None = None):
        cpu = os.cpu_count() or 2
        requested = max_workers if max_workers is not None else int(os.getenv("BRAIN_BACKGROUND_WORKERS", str(min(4, cpu))))
        self.max_workers = max(1, min(int(requested), 8, max(1, cpu)))
        self.max_pending = max(1, int(max_pending))
        self.handlers = dict(handlers or {})
        self.db_path = Path(db_path or os.getenv("BRAIN_BACKGROUND_DB", ".brain/state/background_work.sqlite3"))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._db = sqlite3.connect(str(self.db_path), check_same_thread=False, timeout=10)
        self._db.row_factory = sqlite3.Row
        with self._lock:
            self._db.execute("""CREATE TABLE IF NOT EXISTS background_jobs(
                job_id TEXT PRIMARY KEY, kind TEXT NOT NULL, state TEXT NOT NULL,
                reality TEXT NOT NULL, created_at REAL NOT NULL, started_at REAL,
                finished_at REAL, result_json TEXT, error TEXT, idempotency_key TEXT UNIQUE)""")
            self._db.execute("CREATE INDEX IF NOT EXISTS idx_background_jobs_state ON background_jobs(state,created_at)")
            # A RUNNING job may have been interrupted by process death. These
            # allowlisted deterministic jobs are safe to replay.
            self._db.execute("UPDATE background_jobs SET state='QUEUED',started_at=NULL WHERE state='RUNNING'")
            self._db.commit()
        self._executor = ThreadPoolExecutor(max_workers=self.max_workers, thread_name_prefix="brain-sim-bg")
        self._futures: dict[str, Future] = {}
        self._closed = False
        self._counts = {"submitted": 0, "completed": 0, "failed": 0, "rejected": 0}
        if autostart:
            self.resume_pending()

    def submit(self, kind: str, *, idempotency_key: str | None = None) -> dict[str, Any]:
        kind = str(kind or "").strip()
        if kind not in self.ALLOWED:
            with self._lock: self._counts["rejected"] += 1
            return {"ok": False, "status": "BACKGROUND_JOB_NOT_ALLOWLISTED"}
        with self._lock:
            if self._closed:
                return {"ok": False, "status": "BACKGROUND_COORDINATOR_CLOSED"}
            if idempotency_key:
                row = self._db.execute("SELECT * FROM background_jobs WHERE idempotency_key=?", (idempotency_key,)).fetchone()
                if row:
                    return {"ok": True, "status": "DUPLICATE_RETURNED_EXISTING", "job": self._public(dict(row))}
            unfinished = self._db.execute("SELECT COUNT(*) n FROM background_jobs WHERE state IN ('QUEUED','RUNNING')").fetchone()["n"]
            if unfinished >= self.max_pending:
                self._counts["rejected"] += 1
                return {"ok": False, "status": "BACKPRESSURE", "max_pending": self.max_pending}
            job_id = uuid4().hex
            now = time.time()
            self._db.execute("INSERT INTO background_jobs(job_id,kind,state,reality,created_at,idempotency_key) VALUES(?,?,?,?,?,?)",
                             (job_id, kind, "QUEUED", "SIMULATED", now, idempotency_key))
            self._db.commit()
            self._counts["submitted"] += 1
            item = self._get_locked(job_id)
            self._schedule_locked(job_id, kind)
            return {"ok": True, "status": "QUEUED", "job": self._public(item)}

    def resume_pending(self) -> dict[str, Any]:
        with self._lock:
            if self._closed:
                return {"ok": False, "status": "BACKGROUND_COORDINATOR_CLOSED"}
            rows = self._db.execute("SELECT job_id,kind FROM background_jobs WHERE state='QUEUED' ORDER BY created_at").fetchall()
            count = 0
            for row in rows:
                if row["job_id"] not in self._futures:
                    self._schedule_locked(row["job_id"], row["kind"])
                    count += 1
            return {"ok": True, "resumed": count}

    def _schedule_locked(self, job_id: str, kind: str) -> None:
        self._futures[job_id] = self._executor.submit(self._run, job_id, kind)

    def _run(self, job_id: str, kind: str) -> None:
        with self._lock:
            cur = self._db.execute("UPDATE background_jobs SET state='RUNNING',started_at=? WHERE job_id=? AND state='QUEUED'",
                                   (time.time(), job_id))
            self._db.commit()
            if cur.rowcount != 1: return
        try:
            handler = self.handlers.get(kind)
            if handler is not None:
                result = handler()
                if not isinstance(result, dict):
                    raise TypeError("BACKGROUND_HANDLER_MUST_RETURN_MAPPING")
            elif kind == "simulation_health":
                result = {"healthy": True, "worker_pool": "bounded", "policy": "SIMULATION_FIRST"}
            elif kind == "simulation_inventory":
                result = {"virtual_node": "arkan", "inventory": ["cpu", "memory", "disk", "network", "services", "vms"]}
            elif kind == "simulation_readiness":
                result = {"ready": True, "checks": {"auth_boundary": "NOT_BYPASSED",
                    "real_device_access": "DISABLED", "reality_label": "SIMULATED"}}
            else:
                raise ValueError("BACKGROUND_JOB_NOT_ALLOWLISTED")
            with self._lock:
                self._db.execute("UPDATE background_jobs SET state='COMPLETED',result_json=?,finished_at=? WHERE job_id=?",
                                 (json.dumps(result, ensure_ascii=False), time.time(), job_id))
                self._db.commit()
                self._counts["completed"] += 1
        except Exception as exc:
            with self._lock:
                self._db.execute("UPDATE background_jobs SET state='FAILED',error=?,finished_at=? WHERE job_id=?",
                                 (f"{type(exc).__name__}:{exc}", time.time(), job_id))
                self._db.commit()
                self._counts["failed"] += 1

    @staticmethod
    def _public(item: dict[str, Any]) -> dict[str, Any]:
        item = dict(item)
        item["result"] = json.loads(item.pop("result_json")) if item.get("result_json") else None
        item.pop("idempotency_key", None)
        return item

    def _get_locked(self, job_id: str) -> dict[str, Any] | None:
        row = self._db.execute("SELECT * FROM background_jobs WHERE job_id=?", (job_id,)).fetchone()
        return dict(row) if row else None

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            item = self._get_locked(job_id)
            return self._public(item) if item else None

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            states = {r["state"]: r["n"] for r in self._db.execute("SELECT state,COUNT(*) n FROM background_jobs GROUP BY state")}
            counts = {**self._counts, "persisted_total": self._db.execute("SELECT COUNT(*) n FROM background_jobs").fetchone()["n"]}
            rows = self._db.execute("SELECT * FROM background_jobs ORDER BY created_at DESC LIMIT 50").fetchall()
            return {"ok": True, "runtime": "durable-background-simulation-coordinator",
                    "policy": "SIMULATION_FIRST", "reality": "SIMULATED",
                    "max_workers": self.max_workers, "max_pending": self.max_pending,
                    "closed": self._closed, "db_path": str(self.db_path),
                    "counts": counts, "states": states,
                    "jobs": [self._public(dict(x)) for x in rows]}

    def shutdown(self, wait: bool = False) -> None:
        with self._lock:
            if self._closed: return
            self._closed = True
        self._executor.shutdown(wait=wait, cancel_futures=False)
        with self._lock:
            self._db.close()
