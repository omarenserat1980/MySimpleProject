"""Unified Brain worker routing with workload admission.

This is an admission/routing layer, not an executor. It keeps GitHub as CI,
while preferring cloud/local/device workers for eligible work.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from .workload_controller import WorkloadController

@dataclass(frozen=True)
class WorkerTarget:
    worker_id:str
    kind:str
    capabilities:frozenset[str]
    online:bool=True

class WorkloadRouter:
    def __init__(self, controller:WorkloadController|None=None):
        self.controller=controller or WorkloadController()

    def choose(self, *, queued:int, active:int, priority:str="NORMAL",
               required_capabilities=(), workers=(), github_available:bool=True,
               key_active:int=0, retry_count:int=0, duplicate:bool=False)->dict[str,Any]:
        admission=self.controller.evaluate(
            queued=queued,active=active,key_active=key_active,
            priority=priority,retry_count=retry_count,duplicate=duplicate)
        if not admission["admit"]:
            return {"ok":True,"admit":False,"route":None,"admission":admission}
        required=set(required_capabilities)
        candidates=[w for w in workers if w.online and required.issubset(w.capabilities)]
        # Prefer Brain-owned workers for normal/heavy execution. GitHub is fallback
        # for CI/release-oriented work or when no eligible worker is registered.
        order={"cloud":0,"local":1,"device":2,"github":3}
        candidates.sort(key=lambda w:order.get(w.kind,9))
        target=candidates[0] if candidates else (WorkerTarget("github-actions","github",frozenset({"ci"})) if github_available else None)
        if target is None:
            return {"ok":True,"admit":False,"route":None,"admission":admission,"reason":"NO_WORKER_AVAILABLE"}
        return {"ok":True,"admit":True,"route":{"worker_id":target.worker_id,"kind":target.kind,"capabilities":sorted(target.capabilities)},"admission":admission}
