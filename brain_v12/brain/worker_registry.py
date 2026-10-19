"""Software-only worker registry for Brain routing.

Only software workers may be registered or routed. Physical-device and Termux
agents are intentionally disabled; the legacy constructor flag is ignored.
"""
from __future__ import annotations
from dataclasses import dataclass
import math
import time
from .workload_router import WorkerTarget


@dataclass
class WorkerRecord:
    worker_id: str
    kind: str
    capabilities: frozenset[str]
    online: bool
    last_seen: float
    lease_until: float = 0.0


class WorkerRegistry:
    def __init__(
        self,
        device_bridge=None,
        ttl_seconds: int = 15,
        *,
        include_device_adapters: bool = False,
    ):
        # Compatibility arguments remain accepted but are never activated.
        self.device_bridge = None
        if isinstance(ttl_seconds, bool) or not isinstance(ttl_seconds, int):
            raise ValueError("INVALID_TTL_SECONDS")
        self.ttl_seconds = max(5, ttl_seconds)
        self.include_device_adapters = False
        self._workers = {}

    @staticmethod
    def _timestamp(now):
        value = time.time() if now is None else now
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("INVALID_WORKER_TIMESTAMP")
        value = float(value)
        if not math.isfinite(value):
            raise ValueError("INVALID_WORKER_TIMESTAMP")
        return value

    @staticmethod
    def _lease(lease_seconds):
        if isinstance(lease_seconds, bool) or not isinstance(lease_seconds, int):
            raise ValueError("INVALID_WORKER_LEASE")
        return max(5, lease_seconds)

    @staticmethod
    def _capabilities(capabilities):
        if isinstance(capabilities, (str, bytes)):
            raise ValueError("INVALID_WORKER_CAPABILITIES")
        try:
            values = tuple(capabilities)
        except TypeError as exc:
            raise ValueError("INVALID_WORKER_CAPABILITIES") from exc
        if any(not isinstance(value, str) or not value.strip() for value in values):
            raise ValueError("INVALID_WORKER_CAPABILITIES")
        return frozenset(value.strip() for value in values)

    def register(self, worker_id, kind, capabilities=(), lease_seconds=30, now=None):
        if not isinstance(worker_id, str) or not worker_id.strip():
            raise ValueError("WORKER_ID_REQUIRED")
        worker_id = worker_id.strip()
        if not isinstance(kind, str) or not kind.strip():
            raise ValueError("WORKER_KIND_REQUIRED")
        kind = kind.strip().lower()
        if kind in {"device", "physical", "termux", "android", "hardware"}:
            raise ValueError("PHYSICAL_DEVICE_WORKERS_DISABLED")
        timestamp = self._timestamp(now)
        lease = self._lease(lease_seconds)
        caps = self._capabilities(capabilities)
        rec = WorkerRecord(
            worker_id, kind, caps, True, timestamp, timestamp + lease,
        )
        self._workers[worker_id] = rec
        return self.snapshot(timestamp)

    def heartbeat(self, worker_id, capabilities=None, lease_seconds=30, now=None):
        if not isinstance(worker_id, str) or not worker_id.strip():
            raise ValueError("WORKER_ID_REQUIRED")
        worker_id = worker_id.strip()
        old = self._workers.get(worker_id)
        if old is None:
            raise ValueError("WORKER_NOT_REGISTERED")
        caps = old.capabilities if capabilities is None else self._capabilities(capabilities)
        timestamp = self._timestamp(now)
        lease = self._lease(lease_seconds)
        rec = WorkerRecord(
            worker_id, old.kind, caps, True, timestamp, timestamp + lease,
        )
        self._workers[worker_id] = rec
        return self.snapshot(timestamp)

    def _device_workers(self, now):
        # Deliberately no hardware/Termux discovery in software-only mode.
        return []

    def targets(self, now=None):
        timestamp = self._timestamp(now)
        return [
            WorkerTarget(
                rec.worker_id, rec.kind, rec.capabilities,
                rec.online and rec.lease_until >= timestamp,
            )
            for rec in self._workers.values()
        ]

    def snapshot(self, now=None):
        timestamp = self._timestamp(now)
        return {
            "ok": True,
            "mode": "software-only",
            "device_adapters_enabled": False,
            "workers": [
                {
                    "worker_id": w.worker_id,
                    "kind": w.kind,
                    "capabilities": sorted(w.capabilities),
                    "online": w.online and w.lease_until >= timestamp,
                    "last_seen": w.last_seen,
                    "lease_until": w.lease_until,
                }
                for w in self._workers.values()
            ],
            "device_workers": [],
            "targets": [
                {
                    "worker_id": x.worker_id,
                    "kind": x.kind,
                    "capabilities": sorted(x.capabilities),
                    "online": x.online,
                }
                for x in self.targets(timestamp)
            ],
        }

    def _device_records(self, now):
        return []

    def unregister(self, worker_id):
        self._workers.pop(worker_id, None)
        return self.snapshot()
