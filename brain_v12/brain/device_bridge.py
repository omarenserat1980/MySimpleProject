"""Authenticated, allowlisted, persistent bridge between Brain V12 and a Termux device agent."""
from __future__ import annotations
import hmac, os, time
from uuid import uuid4

AGENT_KEY_ENV = "TERMUX_AGENT_KEY"

HEARTBEAT_STALE = "STALE"

class DeviceBridge:
    ALLOWED_TASKS = {"status": {}, "python_version": {}, "termux_path": {}, "platform": {}}

    def __init__(self, store):
        self.store = store
        self._last_seen = None

    def configured(self):
        return bool(os.getenv(AGENT_KEY_ENV, ""))

    def authenticate(self, supplied):
        expected = os.getenv(AGENT_KEY_ENV, "")
        return bool(expected and supplied and hmac.compare_digest(supplied, expected))

    def enqueue(self, task, params=None):
        if task not in self.ALLOWED_TASKS:
            return {"ok": False, "status": "TASK_NOT_ALLOWED", "allowed": sorted(self.ALLOWED_TASKS)}
        item = {
            "task_id": "DEV-" + uuid4().hex[:12],
            "task": task,
            "params": params or {},
            "created_at": time.time(),
            "status": "QUEUED",
        }
        self.store.device_task_create(item["task_id"], task, item["params"], item["created_at"])
        return {"ok": True, "task": item}

    def poll(self, agent_id):
        if not agent_id:
            return {"ok": False, "status": "AGENT_ID_REQUIRED"}
        self._last_seen = time.time()
        self.store.device_agent_touch(agent_id, self._last_seen)
        item = self.store.device_task_claim(agent_id)
        return {"ok": True, "task": item, "status": "IDLE" if item is None else "CLAIMED"}

    def heartbeat(self, agent_id):
        if not agent_id:
            return {"ok": False, "status": "AGENT_ID_REQUIRED"}
        now = time.time()
        self._last_seen = now
        self.store.device_agent_touch(agent_id, now)
        return {"ok": True, "agent_id": agent_id, "last_seen": now}

    def report(self, task_id, agent_id, ok, result=None, error=""):
        status = self.store.device_task_report(task_id, agent_id, ok, result or {}, error)
        if status is None:
            return {"ok": False, "status": "TASK_NOT_FOUND"}
        if status == "AGENT_MISMATCH":
            return {"ok": False, "status": status}
        return {"ok": True, "status": status, "task": self.store.device_task_get(task_id)}

    def result(self, task_id):
        item = self.store.device_task_get(task_id)
        return {"ok": bool(item), "task": item} if item else {"ok": False, "status": "RESULT_NOT_FOUND"}

    def verify_result(self, task_id):
        """Independent Brain-side verification for the first smoke test."""
        item = self.store.device_task_get(task_id)
        if not item:
            return {"ok": False, "status": "RESULT_NOT_FOUND", "verified": False}
        if item.get("status") != "COMPLETED":
            return {"ok": False, "status": "NOT_COMPLETED", "verified": False, "task": item}

        task = item.get("task")
        result = item.get("result") or {}

        if task == "python_version":
            stdout = str(result.get("stdout", "")).strip()
            exit_code = result.get("returncode", result.get("exit_code"))
            verified = bool(stdout) and (exit_code in (None, 0))
            return {
                "ok": verified,
                "verified": verified,
                "status": "VERIFIED" if verified else "VERIFICATION_FAILED",
                "checks": {
                    "task": task,
                    "stdout_present": bool(stdout),
                    "exit_code_ok": exit_code in (None, 0),
                },
                "task_id": task_id,
                "result": result,
            }

        if task in self.ALLOWED_TASKS:
            ok = bool(item.get("ok"))
            return {
                "ok": ok,
                "verified": ok,
                "status": "VERIFIED" if ok else "VERIFICATION_FAILED",
                "task_id": task_id,
                "result": result,
            }

        return {"ok": False, "verified": False, "status": "TASK_NOT_ALLOWED"}

    def wait_result(self, task_id, timeout=20):
        deadline = time.time() + max(0.1, timeout)
        while time.time() < deadline:
            r = self.result(task_id)
            if r.get("ok") and r.get("task", {}).get("status") in ("COMPLETED", "FAILED"):
                return r
            time.sleep(.5)
        return {"ok": False, "status": "RESULT_TIMEOUT", "task_id": task_id}

    def agent_status(self):
        ttl = max(5, int(os.getenv("TERMUX_AGENT_TTL_SECONDS", "15")))
        now = time.time()
        agents = []
        for item in self.store.device_agents():
            age = max(0.0, now - float(item.get("last_seen", 0)))
            agents.append({
                "agent_id": item["agent_id"],
                "last_seen": item["last_seen"],
                "age_seconds": round(age, 2),
                "online": age <= ttl,
                "state": "ONLINE" if age <= ttl else HEARTBEAT_STALE,
            })
        return {
            "ttl_seconds": ttl,
            "online": any(x["online"] for x in agents),
            "agents": agents,
        }

    def queued_tasks(self):
        return self.store.device_task_counts()

    def heartbeat_age_seconds(self, agent_id):
        for item in self.store.device_agents():
            if item["agent_id"] == agent_id:
                return max(0.0, time.time() - float(item["last_seen"]))
        return None

    def status(self):
        counts = self.store.device_task_counts()
        return {
            "ok": True,
            "configured": self.configured(),
            "auth_env": AGENT_KEY_ENV,
            "queued": counts.get("QUEUED", 0),
            "pending": counts.get("CLAIMED", 0),
            "completed": counts.get("COMPLETED", 0),
            "failed": counts.get("FAILED", 0),
            "last_agent_seen": self._last_seen,
            "agents": self.agent_status(),
        }
