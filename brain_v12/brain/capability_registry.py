from __future__ import annotations
from dataclasses import dataclass, field

@dataclass(frozen=True)
class ExecutorCapability:
    executor_id: str
    capabilities: frozenset[str]
    state: str = "ONLINE"
    metadata: dict = field(default_factory=dict)

class CapabilityRegistry:
    """Brain-owned registry; scheduling depends on capabilities, not device identity."""
    def __init__(self):
        self._items: dict[str, ExecutorCapability] = {}

    def register(self, executor_id, capabilities, metadata=None):
        item=ExecutorCapability(executor_id,frozenset(capabilities),"ONLINE",metadata or {})
        self._items[executor_id]=item
        return item

    def offline(self, executor_id):
        item=self._items.get(executor_id)
        if not item: return False
        self._items[executor_id]=ExecutorCapability(item.executor_id,item.capabilities,"OFFLINE",item.metadata)
        return True

    def online(self, executor_id):
        item=self._items.get(executor_id)
        if not item: return False
        self._items[executor_id]=ExecutorCapability(item.executor_id,item.capabilities,"ONLINE",item.metadata)
        return True

    def select(self, required):
        required=set(required)
        matches=[x for x in self._items.values() if x.state=="ONLINE" and required.issubset(x.capabilities)]
        return sorted(matches,key=lambda x:x.executor_id)

    def status(self):
        return {"count":len(self._items),"online":sum(x.state=="ONLINE" for x in self._items.values()),
                "executors":[{"executor_id":x.executor_id,"capabilities":sorted(x.capabilities),"state":x.state,
                              "metadata":x.metadata} for x in self._items.values()]}
