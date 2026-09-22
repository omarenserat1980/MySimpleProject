from collections import defaultdict
class EventBus:
    def __init__(self,store=None): self.store=store; self.listeners=defaultdict(list)
    def subscribe(self,event_type,callback): self.listeners[event_type].append(callback)
    def publish(self,event_type,payload=None):
        payload=payload or {}; event={"type":event_type,"payload":payload}
        if self.store: self.store.event(event_type,payload)
        for cb in list(self.listeners.get(event_type,[])):
            try: cb(event)
            except Exception: pass
        return event
