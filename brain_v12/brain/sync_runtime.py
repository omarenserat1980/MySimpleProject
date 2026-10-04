"""Offline-first synchronization runtime for Brain replicas.

This layer binds the deterministic SyncStore to a durable local queue and
heartbeat/reconciliation evidence. It deliberately performs no external
side-effects: callers provide the transport and authorization boundary.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
import hashlib, json, os, time
from pathlib import Path
from typing import Any, Callable, Iterable

from .sync_engine import BrainSyncStore, SyncEvent

@dataclass(frozen=True)
class QueueItem:
    event: SyncEvent
    state: str = "PENDING"
    attempts: int = 0
    last_error: str = ""

@dataclass(frozen=True)
class Heartbeat:
    agent_id: str
    sequence: int
    timestamp: float
    status: str
    metadata: dict[str, Any]

class DurableSyncQueue:
    """Append-only JSONL queue with deterministic replay and acknowledgements."""

    def __init__(self, path: str | os.PathLike[str]):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._items: dict[str, QueueItem] = {}
        self._load()

    @staticmethod
    def _event_from_dict(raw: dict[str, Any]) -> SyncEvent:
        return SyncEvent(**raw)

    def _load(self) -> None:
        if not self.path.exists():
            return
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            raw=json.loads(line)
            event=self._event_from_dict(raw["event"])
            self._items[event.event_id]=QueueItem(event, raw.get("state","PENDING"),
                                                  int(raw.get("attempts",0)), raw.get("last_error",""))

    def _persist(self) -> None:
        tmp=self.path.with_suffix(self.path.suffix+".tmp")
        rows=[]
        for item in self._items.values():
            rows.append(json.dumps({"event":asdict(item.event),"state":item.state,
                                    "attempts":item.attempts,"last_error":item.last_error},
                                   sort_keys=True, ensure_ascii=False))
        tmp.write_text("\n".join(rows)+("\n" if rows else ""),encoding="utf-8")
        os.replace(tmp,self.path)

    def enqueue(self,event: SyncEvent) -> bool:
        if event.event_id in self._items:
            return False
        self._items[event.event_id]=QueueItem(event)
        self._persist()
        return True

    def pending(self) -> list[QueueItem]:
        return [x for x in self._items.values() if x.state in {"PENDING","FAILED"}]

    def ack(self,event_id: str) -> None:
        item=self._items.get(event_id)
        if item is None: return
        self._items[event_id]=QueueItem(item.event,"ACKED",item.attempts,item.last_error)
        self._persist()

    def fail(self,event_id: str,error: str) -> None:
        item=self._items.get(event_id)
        if item is None: return
        self._items[event_id]=QueueItem(item.event,"FAILED",item.attempts+1,error[:1000])
        self._persist()

    def replay(self, sender: Callable[[SyncEvent], Any], *, max_items: int | None = None) -> dict[str,int]:
        sent=acked=failed=0
        for item in self.pending()[:max_items]:
            sent += 1
            try:
                sender(item.event)
                self.ack(item.event.event_id); acked += 1
            except Exception as exc:
                self.fail(item.event.event_id, f"{type(exc).__name__}:{exc}"); failed += 1
        return {"sent":sent,"acked":acked,"failed":failed}

    def counts(self) -> dict[str,int]:
        out={k:0 for k in ("PENDING","FAILED","ACKED")}
        for item in self._items.values(): out[item.state]=out.get(item.state,0)+1
        return out

class HeartbeatRegistry:
    def __init__(self, ttl_seconds: float = 30):
        self.ttl_seconds=max(1.0,float(ttl_seconds))
        self._items: dict[str,Heartbeat]={}

    def touch(self,agent_id: str, *, status: str="ONLINE", metadata: dict[str,Any] | None=None, timestamp: float | None=None) -> Heartbeat:
        previous=self._items.get(agent_id)
        hb=Heartbeat(agent_id,(previous.sequence+1 if previous else 1),timestamp if timestamp is not None else time.time(),status,metadata or {})
        self._items[agent_id]=hb
        return hb

    def status(self,now: float | None=None) -> list[dict[str,Any]]:
        now=time.time() if now is None else now
        out=[]
        for hb in self._items.values():
            age=max(0.0,now-hb.timestamp)
            out.append({**asdict(hb),"age_seconds":age,"online":age<=self.ttl_seconds})
        return out

    def is_online(self,agent_id: str, now: float | None=None) -> bool:
        return any(x["agent_id"]==agent_id and x["online"] for x in self.status(now))

def reconcile(local: BrainSyncStore, remote: BrainSyncStore, queue: DurableSyncQueue) -> dict[str,Any]:
    """Apply queued local events to remote and return evidence-grade digests."""
    before=remote.snapshot()["digest"]
    result=queue.replay(lambda event: remote.apply([event]))
    after=remote.snapshot()["digest"]
    return {
        "status":"RECONCILED" if not result["failed"] else "PARTIAL",
        "queue":result,
        "local_digest":local.snapshot()["digest"],
        "remote_digest_before":before,
        "remote_digest_after":after,
        "remote_audit_chain_valid":remote.audit_chain_valid(),
        "evidence_digest":hashlib.sha256(json.dumps(
            {"before":before,"after":after,"queue":result},sort_keys=True,separators=(",",":")
        ).encode()).hexdigest(),
    }
