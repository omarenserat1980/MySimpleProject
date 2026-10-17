"""Provider-neutral task envelope for distributed Brain execution."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class TaskEnvelope:
    schema_version: int
    task_id: str
    idempotency_key: str
    intent_hash: str
    requested_capabilities: tuple[str, ...]
    authorization_scope: str
    max_cost_usd: str
    payload: Mapping[str, Any]

    def validate(self) -> tuple[str, ...]:
        errors: list[str] = []
        if self.schema_version != 1:
            errors.append("SCHEMA_VERSION_UNSUPPORTED")
        if not self.task_id.strip():
            errors.append("TASK_ID_REQUIRED")
        if not self.idempotency_key.strip():
            errors.append("IDEMPOTENCY_KEY_REQUIRED")
        if not self.intent_hash.strip():
            errors.append("INTENT_HASH_REQUIRED")
        if not self.authorization_scope.strip():
            errors.append("AUTHORIZATION_SCOPE_REQUIRED")
        if self.max_cost_usd != "0":
            errors.append("NONZERO_OR_UNCONFIRMED_COST_BLOCKED")
        if not self.requested_capabilities:
            errors.append("CAPABILITY_REQUIRED")
        if not isinstance(self.payload, Mapping):
            errors.append("PAYLOAD_MUST_BE_MAPPING")
        return tuple(errors)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "task_id": self.task_id,
            "idempotency_key": self.idempotency_key,
            "intent_hash": self.intent_hash,
            "requested_capabilities": list(self.requested_capabilities),
            "authorization_scope": self.authorization_scope,
            "max_cost_usd": self.max_cost_usd,
            "payload": dict(self.payload),
            "valid": not self.validate(),
            "validation_errors": list(self.validate()),
            "execution_performed": False,
        }
