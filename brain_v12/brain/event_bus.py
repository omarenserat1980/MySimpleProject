"""In-process event bus with durable-store integration hooks."""
from collections import defaultdict
from typing import Callable, Any

class EventBus:
    def __init__(self, store=None):
        self.store = store
        self.listeners: dict[str, list[Callable[[dict[str, Any]], None]]] = defaultdict(list)

    def subscribe(self, event_type: str, callback: Callable[[dict[str, Any]], None]):
        self.listeners[event_type].append(callback)

    def publish(self, event_type: str, payload: dict[str, Any] | None = None):
        payload = payload or {}
        event = {"type": event_type, "payload": payload}
        if self.store:
            self.store.event(event_type, payload)
        for callback in list(self.listeners.get(event_type, [])):
            try:
                callback(event)
            except Exception:
                pass
        return event
