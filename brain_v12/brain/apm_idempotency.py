"""Idempotency keys and duplicate-claim protection for APM units."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass


@dataclass(frozen=True)
class IdempotencyKey:
    unit_id: str
    input_fingerprint: str
    key: str

    @classmethod
    def create(cls, unit_id: str, input_fingerprint: str) -> "IdempotencyKey":
        if not unit_id or not input_fingerprint:
            raise ValueError("unit_id and input_fingerprint are required")
        raw = json.dumps(
            {"unit_id": unit_id, "input_fingerprint": input_fingerprint},
            sort_keys=True,
            separators=(",", ":"),
        )
        key = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        return cls(unit_id, input_fingerprint, key)


class APMIdempotencyGuard:
    def __init__(self) -> None:
        self.active: dict[str, str] = {}
        self.completed: dict[str, str] = {}

    def acquire(self, key: IdempotencyKey, worker_id: str) -> bool:
        existing = self.active.get(key.key)
        if existing is not None:
            return existing == worker_id
        if key.key in self.completed:
            return False
        self.active[key.key] = worker_id
        return True

    def complete(self, key: IdempotencyKey, result_ref: str) -> None:
        if key.key not in self.active:
            raise ValueError("key is not actively claimed")
        if not result_ref:
            raise ValueError("result_ref is required")
        self.active.pop(key.key)
        self.completed[key.key] = result_ref

    def result(self, key: IdempotencyKey) -> str | None:
        return self.completed.get(key.key)

    def release(self, key: IdempotencyKey) -> None:
        self.active.pop(key.key, None)
