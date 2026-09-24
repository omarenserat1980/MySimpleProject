"""Authenticated, allowlisted bridge between Brain V12 and a Termux device agent."""
from __future__ import annotations

import hmac
import os
import threading
import time
from collections import deque
from uuid import uuid4


class DeviceBridge:
    ALLOWED_TASKS = {
        "status": {},
        "python_version": {},
        "termux_path": {},
        "platform": {},
    }

    def __init__(self):
        self._lock = threading.Lock()
        self._queue = deque()
        self._pending = {}
        self._results = {}
        self._last_seen = None

    def configured(self) -> bool:
        return bool(os.getenv("V12_AGENT_KEY", ""))

    def _auth(self, supplied: str) -> bool:
        expected = os.getenv("V12_AGENT_KEY", "")
        return bool(expected and supplied and hmac.compare_digest(supplied, expected))

    def authenticate(self, supplied: str) -> bool:
        return self._auth(supplied)

    def enqueue(self, task: str, params: dict | None = None) -> dict:
        if task not in self.ALLOWED_TASKS:
            return {"ok": False, "status": "TASK_NOT_ALLOWED", "allowed": sorted(self.ALLOWED_TASKS)}
        item = {
            "task_id": "DEV-" + uuid4().hex[:12],
            "task": task,
            "params": params or {},
            "created_at": time.time(),
            "status": "QUEUED",
        }
        with self._lock:
            self._queue.append(item)
            self._pending[item["task_id"]] = item
        return {"ok": True, "task": item}

    def poll(self, agent_id: str) -> dict:
        if not agent_id:
            return {"ok": False, "status": "AGENT_ID_REQUIRED"}
        with self._lock:
            self._last_seen = time.time()
            while self._queue:
                item = self._queue.popleft()
                item["status"] = "CLAIMED"
                item["claimed_by"] = agent_id
                item["claimed_at"] = time.time()
                return {"ok": True, "task": item}
        return {"ok": True, "task": None, "status": "IDLE"}

    def report(self, task_id: str, agent_id: str, ok: bool, result: dict | None = None, error: str = "") -> dict:
        with self._lock:
            item = self._pending.get(task_id)
            if not item:
                return {"ok": False, "status": "TASK_NOT_FOUND"}
            if item.get("claimed_by") != agent_id:
                return {"ok": False, "status": "AGENT_MISMATCH"}
            item["status"] = "COMPLETED" if ok else "FAILED"
            item["completed_at"] = time.time()
            item["result"] = result or {}
            item["error"] = error[:1000]
            self._results[task_id] = dict(item)
            self._pending.pop(task_id, None)
            return {"ok": True, "status": item["status"], "task": item}

    def status(self) -> dict:
        with self._lock:
            return {
                "ok": True,
                "configured": self.configured(),
                "queued": len(self._queue),
                "pending": len(self._pending),
                "completed": len(self._results),
                "last_agent_seen": self._last_seen,
            }

    def result(self, task_id: str) -> dict:
        with self._lock:
            item = self._results.get(task_id)
            return {"ok": bool(item), "task": item} if item else {"ok": False, "status": "RESULT_NOT_FOUND"}
