"""Versioned, provider-neutral contract for Electronic Brain executors.

The contract describes an operation; it does not grant permission or execute it.
Execution success is distinct from objective verification.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping
import hashlib
import json

SCHEMA_VERSION = "1.0"
ALLOWED_STATUSES = frozenset({
    "QUEUED", "RUNNING", "COMPLETED", "FAILED", "CANCELLED",
    "TIMED_OUT", "UNKNOWN", "NOT_VERIFIED", "VERIFIED_COMPLETED",
})
_SECRET_MARKERS = ("password", "secret", "token", "authorization", "api_key", "private_key")


def _canonical_digest(value: Mapping[str, Any]) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _contains_secret_key(value: Any, path: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key).lower()
            current = f"{path}.{key}" if path else str(key)
            if any(marker in key_text for marker in _SECRET_MARKERS):
                found.append(current)
            else:
                found.extend(_contains_secret_key(child, current))
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            found.extend(_contains_secret_key(child, f"{path}[{index}]"))
    return found


@dataclass(frozen=True)
class ExecutorRequest:
    operation: str
    context: Mapping[str, Any] = field(default_factory=dict)
    permissions: frozenset[str] = frozenset()
    constraints: Mapping[str, Any] = field(default_factory=dict)
    task_id: str = ""
    idempotency_key: str = ""
    intent_hash: str = ""
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("UNSUPPORTED_SCHEMA_VERSION")
        if not self.operation.strip():
            raise ValueError("OPERATION_REQUIRED")
        if not self.task_id.strip() or not self.idempotency_key.strip():
            raise ValueError("TASK_ID_AND_IDEMPOTENCY_KEY_REQUIRED")
        if _contains_secret_key(self.context) or _contains_secret_key(self.constraints):
            raise ValueError("SECRET_MATERIAL_NOT_ALLOWED_IN_EXECUTOR_REQUEST")
        if not isinstance(self.context, Mapping) or not isinstance(self.constraints, Mapping):
            raise ValueError("CONTEXT_AND_CONSTRAINTS_MUST_BE_OBJECTS")
        expected = self.computed_intent_hash()
        if self.intent_hash and self.intent_hash != expected:
            raise ValueError("INTENT_HASH_MISMATCH")
        if not self.intent_hash:
            object.__setattr__(self, "intent_hash", expected)

    def computed_intent_hash(self) -> str:
        return _canonical_digest({
            "schema_version": self.schema_version,
            "task_id": self.task_id,
            "operation": self.operation,
            "context": self.context,
            "permissions": sorted(self.permissions),
            "constraints": self.constraints,
            "idempotency_key": self.idempotency_key,
        })

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["permissions"] = sorted(self.permissions)
        return result


@dataclass(frozen=True)
class ExecutorResult:
    status: str
    result: Any = None
    evidence: tuple[Mapping[str, Any], ...] = ()
    verification_data: Mapping[str, Any] = field(default_factory=dict)
    error: str | None = None
    next_hint: str | None = None
    task_id: str = ""
    executor_id: str = ""
    idempotency_key: str = ""
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("UNSUPPORTED_SCHEMA_VERSION")
        if self.status not in ALLOWED_STATUSES:
            raise ValueError("INVALID_EXECUTOR_STATUS")
        if not self.task_id.strip() or not self.idempotency_key.strip():
            raise ValueError("TASK_ID_AND_IDEMPOTENCY_KEY_REQUIRED")
        if self.status == "VERIFIED_COMPLETED":
            verified = self.verification_data.get("objective_verified") is True
            has_evidence = bool(self.evidence)
            if not verified or not has_evidence:
                raise ValueError("VERIFIED_COMPLETED_REQUIRES_OBJECTIVE_VERIFICATION_AND_EVIDENCE")
        if self.status in {"FAILED", "TIMED_OUT", "UNKNOWN"} and not self.error:
            raise ValueError("FAILURE_OR_UNKNOWN_REQUIRES_ERROR")

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["evidence"] = [dict(item) for item in self.evidence]
        return value
