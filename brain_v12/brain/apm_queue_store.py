"""Durable JSON store for APM queue state."""

from __future__ import annotations

from pathlib import Path
import json

from .apm_queue import APMQueue, QueueUnit


class APMQueueStore:
    def save(self, queue: APMQueue, path: str) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "units": [
                {
                    "unit_id": u.unit_id,
                    "depends_on": list(u.depends_on),
                    "priority": u.priority,
                    "state": u.state,
                    "attempt": u.attempt,
                    "worker_id": u.worker_id,
                }
                for u in queue.units.values()
            ],
        }
        p.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def load(self, path: str) -> APMQueue:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if payload.get("version") != 1:
            raise ValueError("unsupported queue state version")
        units = [
            QueueUnit(
                unit_id=item["unit_id"],
                depends_on=tuple(item.get("depends_on", [])),
                priority=int(item.get("priority", 100)),
                state=item.get("state", "QUEUED"),
                attempt=int(item.get("attempt", 0)),
                worker_id=item.get("worker_id"),
            )
            for item in payload.get("units", [])
        ]
        return APMQueue(units)

    def recover_workers(self, queue: APMQueue) -> int:
        """Convert abandoned claimed work back to QUEUED for safe retry."""
        recovered = 0
        for unit in queue.units.values():
            if unit.state == "CLAIMED":
                unit.state = "QUEUED"
                unit.worker_id = None
                recovered += 1
        return recovered
