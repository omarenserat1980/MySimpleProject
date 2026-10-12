"""Task/Evidence synchronization adapter.

Converts observable lifecycle transitions into deterministic sync records.
It does not execute tasks or external side effects.
"""
from __future__ import annotations
import hashlib, json
from typing import Any, Mapping
from uuid import uuid4

from .sync_engine import BrainSyncStore, SyncEvent, SyncConflict
from .sync_runtime import DurableSyncQueue

class TaskSyncAdapter:
    def __init__(self, store: BrainSyncStore, queue: DurableSyncQueue):
        self.store=store
        self.queue=queue

    def publish_task(self, task: Mapping[str, Any], *, event_id: str | None = None) -> SyncEvent:
        task_id=str(task.get("id") or task.get("task_id") or "")
        if not task_id:
            raise ValueError("TASK_ID_REQUIRED")
        key=f"task/{task_id}"
        event=self.store.put(key, dict(task), event_id=event_id or f"task-sync-{uuid4().hex}")
        self.queue.enqueue(event)
        return event

    def publish_evidence(self, task_id: str, evidence: Mapping[str, Any], *, event_id: str | None = None) -> SyncEvent:
        payload=dict(evidence)
        payload["task_id"]=task_id
        payload["evidence_digest"]=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
        key=f"evidence/{task_id}"
        event=self.store.put(key,payload,event_id=event_id or f"evidence-sync-{uuid4().hex}")
        self.queue.enqueue(event)
        return event

    def publish_transition(self, task: Mapping[str, Any], *, evidence: Mapping[str, Any] | None = None) -> dict[str,Any]:
        task_event=self.publish_task(task)
        evidence_event=None
        if evidence is not None:
            evidence_event=self.publish_evidence(str(task_event.value.get("id") or task_event.value.get("task_id")),evidence)
        return {"task_event_id":task_event.event_id,"evidence_event_id":evidence_event.event_id if evidence_event else None,
                "queue_state":self.queue.counts()}

    def conflict_safe_update(self,key:str,value:Mapping[str,Any],expected_revision:int,event_id:str)->dict[str,Any]:
        try:
            event=self.store.put(key,value,expected_revision=expected_revision,event_id=event_id)
            self.queue.enqueue(event)
            return {"ok":True,"event_id":event.event_id,"revision":event.revision}
        except SyncConflict as exc:
            return {"ok":False,"status":"CONFLICT","key":exc.key,"expected":exc.expected,"actual":exc.actual}
