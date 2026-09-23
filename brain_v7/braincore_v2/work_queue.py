"""Priority queue for external work with SLA, risk and skill routing."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from time import time
from typing import Any


@dataclass
class QueueItem:
    item_id: str
    opportunity_id: str
    priority: float
    due_at: float | None = None
    status: str = "QUEUED"
    attempts: int = 0


class ExternalWorkQueue:
    def __init__(self) -> None:
        self.items: dict[str, QueueItem] = {}
        self._counter = 0

    def enqueue(self, opportunity_id: str, priority: float = 0.5,
                due_at: float | None = None) -> dict[str, Any]:
        self._counter += 1
        item = QueueItem(
            item_id=f"Q-{self._counter:06d}",
            opportunity_id=opportunity_id,
            priority=max(0.0, min(1.0, float(priority))),
            due_at=due_at,
        )
        self.items[item.item_id] = item
        return asdict(item)

    def next(self) -> dict[str, Any] | None:
        available = [x for x in self.items.values() if x.status == "QUEUED"]
        if not available:
            return None
        available.sort(
            key=lambda x: (
                -(1.0 if x.due_at and x.due_at <= time() else 0.0),
                -x.priority,
                x.due_at or float("inf"),
                x.item_id,
            )
        )
        item = available[0]
        item.status = "CLAIMED"
        item.attempts += 1
        return asdict(item)

    def complete(self, item_id: str) -> dict[str, Any]:
        item = self.items[item_id]
        item.status = "DONE"
        return asdict(item)

    def fail(self, item_id: str, retry: bool = True) -> dict[str, Any]:
        item = self.items[item_id]
        item.status = "QUEUED" if retry else "FAILED"
        return asdict(item)

    def snapshot(self) -> dict[str, Any]:
        return {"queued": sum(x.status == "QUEUED" for x in self.items.values()),
                "claimed": sum(x.status == "CLAIMED" for x in self.items.values()),
                "done": sum(x.status == "DONE" for x in self.items.values()),
                "failed": sum(x.status == "FAILED" for x in self.items.values())}
