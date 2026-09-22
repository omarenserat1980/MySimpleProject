from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

@dataclass
class BrainEvent:
    source: str
    destination: str
    event_type: str
    payload: dict[str, Any] = field(default_factory=dict)
    importance: float = 0.5
    confidence: float = 1.0
    context: dict[str, Any] = field(default_factory=dict)
    prediction_id: str | None = None
    goal_id: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class EventBus:
    def __init__(self):
        self.history: list[BrainEvent] = []
        self.handlers: dict[str, list[Callable[[BrainEvent], None]]] = {}

    def subscribe(self, event_type: str, handler: Callable[[BrainEvent], None]):
        self.handlers.setdefault(event_type, []).append(handler)

    def publish(self, event: BrainEvent):
        self.history.append(event)
        for handler in self.handlers.get(event.event_type, []):
            handler(event)
        for handler in self.handlers.get("*", []):
            handler(event)
