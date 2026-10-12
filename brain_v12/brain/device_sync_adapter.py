"""Device/task synchronization adapter.

Turns successful local device/task state changes into deterministic sync events and
durable queue entries. The adapter is transport-agnostic and never performs an
external side effect.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Mapping

from .sync_engine import BrainSyncStore, SyncEvent
from .sync_runtime import DurableSyncQueue, Heartbeat, HeartbeatRegistry, reconcile


class DeviceTaskSyncAdapter:
    """Bridge DeviceBridge state transitions to the offline-first sync runtime."""

    def __init__(
        self,
        queue_path: str | Path,
        *,
        replica_id: str = "brain-device",
        heartbeat_ttl: float = 30,
    ) -> None:
        self.store = BrainSyncStore(replica_id)
        self.queue = DurableSyncQueue(queue_path)
        self.heartbeats = HeartbeatRegistry(heartbeat_ttl)
        # Rebuild deterministic local state from durable events after a restart.
        self.store.apply(item.event for item in self.queue.items())

    @staticmethod
    def _event_id(key: str, value: Mapping[str, Any], *, sequence: int | None = None) -> str:
        payload = {"key": key, "value": dict(value)}
        if sequence is not None:
            payload["sequence"] = sequence
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _upsert(self, key: str, value: Mapping[str, Any]) -> SyncEvent:
        current = self.store.get(key)
        event_id = self._event_id(key, value)
        event = self.store.put(
            key,
            value,
            expected_revision=current.revision if current else 0,
            event_id=event_id,
        )
        self.queue.enqueue(event)
        return event

    def task_transition(
        self,
        task_id: str,
        *,
        status: str,
        agent_id: str | None = None,
        task: str | None = None,
        result: Mapping[str, Any] | None = None,
        error: str = "",
        evidence_ref: str | None = None,
    ) -> SyncEvent:
        value = {
            "task_id": task_id,
            "status": status,
            "agent_id": agent_id,
            "task": task,
            "result": dict(result or {}),
            "error": error,
            "evidence_ref": evidence_ref,
        }
        return self._upsert(f"device/task/{task_id}", value)

    def heartbeat(
        self,
        agent_id: str,
        *,
        metadata: Mapping[str, Any] | None = None,
        status: str = "ONLINE",
        timestamp: float | None = None,
    ) -> tuple[Heartbeat, SyncEvent]:
        hb = self.heartbeats.touch(
            agent_id,
            status=status,
            metadata=dict(metadata or {}),
            timestamp=timestamp,
        )
        value = {
            "agent_id": agent_id,
            "sequence": hb.sequence,
            "status": hb.status,
            "timestamp": hb.timestamp,
            "metadata": hb.metadata,
        }
        event_id = self._event_id(f"device/agent/{agent_id}", value, sequence=hb.sequence)
        current = self.store.get(f"device/agent/{agent_id}")
        event = self.store.put(
            f"device/agent/{agent_id}",
            value,
            expected_revision=current.revision if current else 0,
            event_id=event_id,
        )
        self.queue.enqueue(event)
        return hb, event

    def pending(self) -> list[SyncEvent]:
        return [item.event for item in self.queue.pending()]

    def reconcile(self, remote: BrainSyncStore) -> dict[str, Any]:
        return reconcile(self.store, remote, self.queue)

    def evidence(self) -> dict[str, Any]:
        snapshot = self.store.snapshot()
        return {
            "status": "VERIFIED" if self.store.audit_chain_valid() else "VERIFICATION_FAILED",
            "digest": snapshot["digest"],
            "revision_count": snapshot["revision_count"],
            "queue": self.queue.counts(),
            "audit_chain_valid": self.store.audit_chain_valid(),
        }
