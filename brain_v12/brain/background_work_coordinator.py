"""Bounded simulation-first background work coordinator for Electronic Brain.

Only allowlisted simulation jobs run here. This module never executes arbitrary
shell commands, contacts real devices, or treats simulated results as REAL.
"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, Future
from threading import RLock
from typing import Any
from uuid import uuid4
import os, time

class BackgroundWorkCoordinator:
    ALLOWED = {"simulation_health", "simulation_inventory", "simulation_readiness"}

    def __init__(self, *, max_workers: int | None = None, max_pending: int = 64):
        cpu = os.cpu_count() or 2
        requested = max_workers if max_workers is not None else int(os.getenv("BRAIN_BACKGROUND_WORKERS", str(min(4, cpu))))
        self.max_workers = max(1, min(int(requested), 8, max(1, cpu)))
        self.max_pending = max(1, int(max_pending))
        self._lock = RLock()
        self._executor = ThreadPoolExecutor(max_workers=self.max_workers, thread_name_prefix="brain-sim-bg")
        self._items: dict[str, dict[str, Any]] = {}
        self._idempotency: dict[str, str] = {}
        self._futures: dict[str, Future] = {}
        self._closed = False
        self._counts = {"submitted": 0, "completed": 0, "failed": 0, "rejected": 0}

    def submit(self, kind: str, *, idempotency_key: str | None = None) -> dict[str, Any]:
        kind = str(kind or "").strip()
        if kind not in self.ALLOWED:
            with self._lock:
                self._counts["rejected"] += 1
            return {"ok": False, "status": "BACKGROUND_JOB_NOT_ALLOWLISTED"}
        with self._lock:
            if self._closed:
                return {"ok": False, "status": "BACKGROUND_COORDINATOR_CLOSED"}
            if idempotency_key and idempotency_key in self._idempotency:
                old_id = self._idempotency[idempotency_key]
                return {"ok": True, "status": "DUPLICATE_RETURNED_EXISTING", "job": self._public(self._items[old_id])}
            unfinished = sum(1 for item in self._items.values() if item["state"] in {"QUEUED", "RUNNING"})
            if unfinished >= self.max_pending:
                self._counts["rejected"] += 1
                return {"ok": False, "status": "BACKPRESSURE", "max_pending": self.max_pending}
            job_id = uuid4().hex
            item = {"job_id": job_id, "kind": kind, "state": "QUEUED", "reality": "SIMULATED",
                    "created_at": time.time(), "started_at": None, "finished_at": None,
                    "result": None, "error": None, "idempotency_key": idempotency_key}
            self._items[job_id] = item
            if idempotency_key:
                self._idempotency[idempotency_key] = job_id
            self._counts["submitted"] += 1
            future = self._executor.submit(self._run, job_id, kind)
            self._futures[job_id] = future
            return {"ok": True, "status": "QUEUED", "job": self._public(item)}

    def _run(self, job_id: str, kind: str) -> None:
        with self._lock:
            item = self._items[job_id]
            item["state"] = "RUNNING"
            item["started_at"] = time.time()
        try:
            # Deterministic work descriptors, intentionally no physical side effects.
            if kind == "simulation_health":
                result = {"healthy": True, "worker_pool": "bounded", "policy": "SIMULATION_FIRST"}
            elif kind == "simulation_inventory":
                result = {"virtual_node": "arkan", "inventory": ["cpu", "memory", "disk", "network", "services", "vms"]}
            else:
                result = {"ready": True, "checks": {"auth_boundary": "NOT_BYPASSED", "real_device_access": "DISABLED",
                          "reality_label": "SIMULATED"}}
            with self._lock:
                item["result"] = result
                item["state"] = "COMPLETED"
                item["finished_at"] = time.time()
                self._counts["completed"] += 1
        except Exception as exc:
            with self._lock:
                item["error"] = f"{type(exc).__name__}:{exc}"
                item["state"] = "FAILED"
                item["finished_at"] = time.time()
                self._counts["failed"] += 1

    @staticmethod
    def _public(item: dict[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in item.items() if k != "idempotency_key"}

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            item = self._items.get(job_id)
            return self._public(item) if item else None

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            states = {}
            for item in self._items.values():
                states[item["state"]] = states.get(item["state"], 0) + 1
            return {"ok": True, "runtime": "background-simulation-coordinator",
                    "policy": "SIMULATION_FIRST", "reality": "SIMULATED",
                    "max_workers": self.max_workers, "max_pending": self.max_pending,
                    "closed": self._closed, "counts": dict(self._counts), "states": states,
                    "jobs": [self._public(x) for x in sorted(self._items.values(), key=lambda x: x["created_at"], reverse=True)[:50]]}

    def shutdown(self, wait: bool = False) -> None:
        with self._lock:
            self._closed = True
        self._executor.shutdown(wait=wait, cancel_futures=True)
