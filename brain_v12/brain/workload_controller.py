"""Brain workload admission and circuit-breaker policy."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

PRIORITIES=("CRITICAL","HIGH","NORMAL","LOW","BACKGROUND")

@dataclass(frozen=True)
class WorkloadPolicy:
    max_total_active:int=20
    max_total_queued:int=300
    max_active_per_key:int=1
    max_retry_attempts:int=2
    emergency_queued:int=800
    congested_queued:int=500
    high_load_queued:int=300

class WorkloadController:
    def __init__(self,policy:WorkloadPolicy|None=None):
        self.policy=policy or WorkloadPolicy()
    def mode(self,queued:int)->str:
        q=max(0,int(queued))
        if q>=self.policy.emergency_queued:return "EMERGENCY"
        if q>=self.policy.congested_queued:return "CONGESTED"
        if q>=self.policy.high_load_queued:return "HIGH_LOAD"
        return "NORMAL"
    def evaluate(self,*,queued:int,active:int,key_active:int=0,priority:str="NORMAL",retry_count:int=0,duplicate:bool=False)->dict[str,Any]:
        p=str(priority).upper()
        if p not in PRIORITIES:p="NORMAL"
        mode=self.mode(queued)
        reason=None
        if duplicate:reason="DUPLICATE"
        elif retry_count>=self.policy.max_retry_attempts and p not in {"CRITICAL","HIGH"}:reason="RETRY_BUDGET_EXHAUSTED"
        elif mode=="EMERGENCY" and p not in {"CRITICAL","HIGH"}:reason="CIRCUIT_BREAKER"
        elif mode=="CONGESTED" and p in {"LOW","BACKGROUND"}:reason="CONGESTION_BACKPRESSURE"
        elif active>=self.policy.max_total_active and p!="CRITICAL":reason="ACTIVE_LIMIT"
        elif key_active>=self.policy.max_active_per_key and p!="CRITICAL":reason="KEY_CONCURRENCY_LIMIT"
        elif queued>=self.policy.max_total_queued and p in {"LOW","BACKGROUND"}:reason="QUEUE_LIMIT"
        return {"ok":True,"admit":reason is None,"mode":mode,"priority":p,"reason":reason or "ADMITTED"}
    def status(self,*,queued:int,active:int,oldest_age_seconds:float|None=None)->dict[str,Any]:
        return {"ok":True,"controller":"brain-workload-v1","mode":self.mode(queued),"queued":max(0,int(queued)),"active":max(0,int(active)),"oldest_age_seconds":oldest_age_seconds,"policy":self.policy.__dict__}
