from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
import json
from time import time
from typing import Any

from .audit import EvidenceLedger
from .state import StateStore


@dataclass(frozen=True)
class StateCheckpoint:
    checkpoint_id: int
    created_at: float
    state: dict[str, Any]
    sha256: str


class RecoveryManager:
    """In-memory, integrity-checked state checkpoints; not a durable backup service."""

    def __init__(self, state: StateStore, evidence: EvidenceLedger) -> None:
        self._state = state
        self._evidence = evidence
        self._checkpoints: list[StateCheckpoint] = []

    @staticmethod
    def _digest(state: dict[str, Any]) -> str:
        try:
            encoded = json.dumps(
                state, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
            ).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise TypeError("checkpoint state must contain finite JSON-compatible values") from exc
        return sha256(encoded).hexdigest()

    def checkpoint(self) -> StateCheckpoint:
        snapshot = self._state.snapshot()
        digest = self._digest(snapshot)
        checkpoint = StateCheckpoint(
            checkpoint_id=len(self._checkpoints) + 1,
            created_at=time(),
            state=deepcopy(snapshot),
            sha256=digest,
        )
        self._checkpoints.append(checkpoint)
        self._evidence.record("recovery.checkpoint", {
            "checkpoint_id": checkpoint.checkpoint_id, "sha256": digest
        })
        return checkpoint

    def restore(self, checkpoint: StateCheckpoint) -> None:
        if not isinstance(checkpoint, StateCheckpoint):
            raise TypeError("checkpoint must be a StateCheckpoint")
        if self._digest(checkpoint.state) != checkpoint.sha256:
            self._evidence.record("recovery.restore_rejected", {
                "checkpoint_id": checkpoint.checkpoint_id, "reason": "digest_mismatch"
            })
            raise ValueError("checkpoint integrity check failed")
        self._state.restore(deepcopy(checkpoint.state))
        self._evidence.record("recovery.restore", {
            "checkpoint_id": checkpoint.checkpoint_id, "sha256": checkpoint.sha256
        })

    def checkpoints(self) -> list[StateCheckpoint]:
        return deepcopy(self._checkpoints)

    def is_ready(self) -> bool:
        return isinstance(self._checkpoints, list)
