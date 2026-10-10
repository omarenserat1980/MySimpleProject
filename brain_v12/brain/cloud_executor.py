"""Initial safe skeleton for the Brain cloud task executor.

This module defines an execution contract only. The initial implementation does
not run arbitrary commands, connect to cloud providers, or launch resources.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


class ExecutorStatus(str, Enum):
    ACCEPTED_FOR_REVIEW = "ACCEPTED_FOR_REVIEW"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class ExecutionRequest:
    task_id: str
    resource_id: str
    operation: str
    intent_hash: str
    max_cost_usd: str = "0"


@dataclass(frozen=True)
class ExecutionReceipt:
    task_id: str
    status: ExecutorStatus
    executor_id: str | None
    executed: bool
    reason: str
    evidence: Mapping[str, Any]


class BrainCloudExecutor:
    """Policy placeholder; execution remains disabled in the initial build."""

    def __init__(self, executor_id: str = "brain-cloud-executor-prototype") -> None:
        self.executor_id = executor_id

    def submit(self, request: ExecutionRequest, *, identity_verified: bool = False,
               resource_available: bool = False, permission_granted: bool = False,
               cost_verified_zero: bool = False) -> ExecutionReceipt:
        """Return a fail-closed receipt without executing the requested task."""
        reasons = []
        if not request.task_id.strip() or not request.resource_id.strip():
            reasons.append("TASK_AND_RESOURCE_REQUIRED")
        if not request.operation.strip() or not request.intent_hash.strip():
            reasons.append("OPERATION_AND_INTENT_HASH_REQUIRED")
        if request.max_cost_usd != "0":
            reasons.append("NONZERO_COST_NOT_ALLOWED")
        if not identity_verified:
            reasons.append("IDENTITY_NOT_VERIFIED")
        if not resource_available:
            reasons.append("RESOURCE_NOT_CONFIRMED_AVAILABLE")
        if not permission_granted:
            reasons.append("PERMISSION_NOT_GRANTED")
        if not cost_verified_zero:
            reasons.append("ZERO_COST_NOT_VERIFIED")
        if reasons:
            return ExecutionReceipt(request.task_id, ExecutorStatus.BLOCKED, None, False,
                                    ";".join(reasons), {"execution_performed": False})
        return ExecutionReceipt(request.task_id, ExecutorStatus.ACCEPTED_FOR_REVIEW,
                                self.executor_id, False,
                                "PROTOTYPE_EXECUTION_DISABLED",
                                {"execution_performed": False, "intent_hash": request.intent_hash})
