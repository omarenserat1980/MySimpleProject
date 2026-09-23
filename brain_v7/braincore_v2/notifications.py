"""Central internal notifications for the Electronic Brain workforce.

Notifications are internal records only. They do not grant external permissions
or perform money movement, credential changes, or irreversible actions.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from time import time
from typing import Any


@dataclass
class Notification:
    notification_id: str
    event_type: str
    priority: str
    sender_id: str
    recipient_id: str
    message: str
    task_id: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time)
    read: bool = False


class NotificationCenter:
    """In-memory event bus with durable-friendly snapshots."""

    PRIORITY_ORDER = {"LOW": 1, "NORMAL": 2, "HIGH": 3, "CRITICAL": 4}

    def __init__(self) -> None:
        self.notifications: dict[str, Notification] = {}
        self._seq = 0

    def _next_id(self) -> str:
        self._seq += 1
        return f"NOTIF-{self._seq:09d}"

    def emit(
        self,
        event_type: str,
        *,
        sender_id: str,
        recipient_id: str,
        message: str,
        priority: str = "NORMAL",
        task_id: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> Notification:
        priority = priority.upper()
        if priority not in self.PRIORITY_ORDER:
            raise ValueError("invalid notification priority")
        item = Notification(
            notification_id=self._next_id(),
            event_type=event_type,
            priority=priority,
            sender_id=sender_id,
            recipient_id=recipient_id,
            message=message,
            task_id=task_id,
            data=dict(data or {}),
        )
        self.notifications[item.notification_id] = item
        return item

    def unread_for(self, recipient_id: str, *, min_priority: str = "LOW") -> list[Notification]:
        threshold = self.PRIORITY_ORDER[min_priority.upper()]
        items = [
            n for n in self.notifications.values()
            if n.recipient_id == recipient_id
            and not n.read
            and self.PRIORITY_ORDER[n.priority] >= threshold
        ]
        return sorted(items, key=lambda n: (-self.PRIORITY_ORDER[n.priority], n.created_at))

    def mark_read(self, notification_id: str) -> None:
        self.notifications[notification_id].read = True

    def snapshot(self) -> dict[str, Any]:
        return {
            "count": len(self.notifications),
            "unread_count": sum(not n.read for n in self.notifications.values()),
            "notifications": [asdict(n) for n in self.notifications.values()],
        }
