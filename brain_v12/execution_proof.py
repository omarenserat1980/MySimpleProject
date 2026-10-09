"""Evidence-first execution state and hash-chain proof for Brain runtime tasks.

This module records the lifecycle of a task independently from the executor's
success claim. It is deliberately storage-agnostic so the Home Server can
persist or export the evidence without granting arbitrary execution power.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any

TERMINAL = {"ACCEPTED", "REJECTED"}
ALLOWED_TRANSITIONS = {
    "QUEUED": {"CLAIMED", "REJECTED"},
    "CLAIMED": {"RUNNING", "REJECTED"},
    "RUNNING": {"RESULT_READY", "FAILED"},
    "RESULT_READY": {"EVIDENCE_READY", "FAILED"},
    "EVIDENCE_READY": {"VERIFYING", "FAILED"},
    "VERIFYING": {"ACCEPTED", "REJECTED"},
    "FAILED": {"VERIFYING", "REJECTED"},
}


class ProofTransitionError(ValueError):
    """Raised when an execution proof attempts an invalid state transition."""


@dataclass(frozen=True)
class EvidenceEvent:
    sequence: int
    state: str
    task_id: str
    worker_id: str
    timestamp: float
    payload: dict[str, Any]
    previous_hash: str
    event_hash: str


class ExecutionProof:
    """In-memory proof chain; callers may persist exported events in SQLite."""

    def __init__(self, task_id: str, worker_id: str, *, now=time.time):
        if not task_id or not worker_id:
            raise ValueError("TASK_AND_WORKER_REQUIRED")
        self.task_id = task_id
        self.worker_id = worker_id
        self._now = now
        self._events: list[EvidenceEvent] = []
        self._append("QUEUED", {"reason": "task_created"})

    @property
    def state(self) -> str:
        return self._events[-1].state

    @property
    def events(self) -> tuple[EvidenceEvent, ...]:
        return tuple(self._events)

    @staticmethod
    def _canonical(value: dict[str, Any]) -> str:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    def _append(self, state: str, payload: dict[str, Any]) -> EvidenceEvent:
        if self._events:
            allowed = ALLOWED_TRANSITIONS.get(self.state, set())
            if state not in allowed:
                raise ProofTransitionError(f"INVALID_TRANSITION:{self.state}->{state}")
        sequence = len(self._events) + 1
        previous_hash = self._events[-1].event_hash if self._events else "GENESIS"
        timestamp = float(self._now())
        body = {
            "sequence": sequence,
            "state": state,
            "task_id": self.task_id,
            "worker_id": self.worker_id,
            "timestamp": timestamp,
            "payload": payload,
            "previous_hash": previous_hash,
        }
        event_hash = hashlib.sha256(self._canonical(body).encode("utf-8")).hexdigest()
        event = EvidenceEvent(
            sequence=sequence,
            state=state,
            task_id=self.task_id,
            worker_id=self.worker_id,
            timestamp=timestamp,
            payload=dict(payload),
            previous_hash=previous_hash,
            event_hash=event_hash,
        )
        self._events.append(event)
        return event

    def transition(self, state: str, **payload: Any) -> EvidenceEvent:
        if self.state in TERMINAL:
            raise ProofTransitionError(f"TERMINAL_STATE:{self.state}")
        return self._append(state, payload)

    @classmethod
    def from_export(cls, exported: dict[str, Any]) -> "ExecutionProof":
        """Rehydrate a persisted proof without creating a new event."""
        if not isinstance(exported, dict) or exported.get("proof_version") != 1:
            raise ValueError("INVALID_PROOF_VERSION")
        task_id = exported.get("task_id", "")
        worker_id = exported.get("worker_id", "")
        events = exported.get("events")
        if not task_id or not worker_id or not isinstance(events, list) or not events:
            raise ValueError("INVALID_PROOF_EXPORT")
        proof = cls.__new__(cls)
        proof.task_id = task_id
        proof.worker_id = worker_id
        proof._now = time.time
        proof._events = [
            EvidenceEvent(
                sequence=int(e["sequence"]), state=e["state"], task_id=e["task_id"],
                worker_id=e["worker_id"], timestamp=float(e["timestamp"]),
                payload=dict(e.get("payload", {})), previous_hash=e["previous_hash"],
                event_hash=e["event_hash"],
            ) for e in events
        ]
        if proof.task_id != proof._events[0].task_id or proof.worker_id != proof._events[0].worker_id:
            raise ValueError("PROOF_IDENTITY_MISMATCH")
        if not proof.verify_chain() or exported.get("state") != proof.state:
            raise ValueError("INVALID_PROOF_CHAIN")
        return proof

    @classmethod
    def verify_export(cls, exported: dict[str, Any]) -> bool:
        try:
            cls.from_export(exported)
            return True
        except (KeyError, TypeError, ValueError, IndexError):
            return False

    def verify_chain(self) -> bool:
        previous = "GENESIS"
        for event in self._events:
            body = {
                "sequence": event.sequence,
                "state": event.state,
                "task_id": event.task_id,
                "worker_id": event.worker_id,
                "timestamp": event.timestamp,
                "payload": event.payload,
                "previous_hash": previous,
            }
            expected = hashlib.sha256(self._canonical(body).encode("utf-8")).hexdigest()
            if event.previous_hash != previous or event.event_hash != expected:
                return False
            previous = event.event_hash
        return True

    def export(self) -> dict[str, Any]:
        return {
            "proof_version": 1,
            "task_id": self.task_id,
            "worker_id": self.worker_id,
            "state": self.state,
            "verified": self.verify_chain(),
            "events": [
                {
                    "sequence": e.sequence,
                    "state": e.state,
                    "task_id": e.task_id,
                    "worker_id": e.worker_id,
                    "timestamp": e.timestamp,
                    "payload": e.payload,
                    "previous_hash": e.previous_hash,
                    "event_hash": e.event_hash,
                }
                for e in self._events
            ],
        }
