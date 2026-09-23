"""Operational health and heartbeat for the Brain workers.

This is intentionally provider-neutral. A deployment is considered live only
when an external provider supplies a recent heartbeat.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from time import time
from typing import Any


@dataclass
class Heartbeat:
    worker_id: str
    timestamp: float
    status: str
    cycle: int = 0
    detail: str = ""


class WorkerHealthRegistry:
    def __init__(self, stale_after_s: int = 180) -> None:
        self.stale_after_s = max(30, int(stale_after_s))
        self._heartbeats: dict[str, Heartbeat] = {}

    def beat(self, worker_id: str, *, status: str = "HEALTHY", cycle: int = 0, detail: str = "") -> dict[str, Any]:
        if not worker_id.strip():
            raise ValueError("worker_id is required")
        hb = Heartbeat(worker_id.strip(), time(), status, int(cycle), detail)
        self._heartbeats[hb.worker_id] = hb
        return asdict(hb)

    def inspect(self, now: float | None = None) -> dict[str, Any]:
        current = time() if now is None else float(now)
        workers = {}
        for worker_id, hb in self._heartbeats.items():
            age = max(0.0, current - hb.timestamp)
            workers[worker_id] = {
                **asdict(hb),
                "age_s": round(age, 2),
                "live": hb.status == "HEALTHY" and age <= self.stale_after_s,
            }
        return {
            "workers": workers,
            "live_workers": sum(x["live"] for x in workers.values()),
            "registry_size": len(workers),
            "stale_after_s": self.stale_after_s,
        }
