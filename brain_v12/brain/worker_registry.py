"""Software-only worker registry for Brain routing.

Only software workers may be registered or routed. Physical-device and Termux
agents are intentionally disabled; the legacy constructor flag is ignored.
"""
from __future__ import annotations
from dataclasses import dataclass
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
        self.ttl_seconds = max(5, int(ttl_seconds))
        self.include_device_adapters = False
        self._workers = {}

    def register(self, worker_id, kind, capabilities=(), lease_seconds=30, now=None):
        worker_id = str(worker_id).strip()
        if not worker_id:
            raise ValueError("WORKER_ID_REQUIRED")
        kind = str(kind).strip().lower()
        if kind in {"device", "physical", "termux", "android", "hardware"}:
            raise ValueError("PHYSICAL_DEVICE_WORKERS_DISABLED")
        now = time.time() if now is None else float(now)
        lease = max(5, int(lease_seconds))
        rec = WorkerRecord(
            worker_id, kind, frozenset(str(c) for c in capabilities),
            True, now, now + lease,
        )
        self._workers[worker_id] = rec
        return self.snapshot(now)

    def heartbeat(self, worker_id, capabilities=None, lease_seconds=30, now=None):
        now = time.time() if now is None else float(now)
        old = self._workers.get(worker_id)
        caps = frozenset(capabilities) if capabilities is not None else (
            old.capabilities if old else frozenset()
        )
        kind = old.kind if old else "software"
        return self.register(worker_id, kind, caps, lease_seconds, now)

    def _device_workers(self, now):
        # Deliberately no hardware/Termux discovery in software-only mode.
        return []

    def targets(self, now=None):
        now = time.time() if now is None else float(now)
        return [
            WorkerTarget(
                rec.worker_id, rec.kind, rec.capabilities,
                rec.online and rec.lease_until >= now,
            )
            for rec in self._workers.values()
        ]

    def snapshot(self, now=None):
        now = time.time() if now is None else float(now)
        return {
            "ok": True,
            "mode": "software-only",
            "device_adapters_enabled": False,
            "workers": [
                {
                    "worker_id": w.worker_id,
                    "kind": w.kind,
                    "capabilities": sorted(w.capabilities),
                    "online": w.online,
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
                for x in self.targets(now)
            ],
        }

    def _device_records(self, now):
        return []

    def unregister(self, worker_id):
        self._workers.pop(worker_id, None)
        return self.snapshot()
