"""Fail-closed coordinator for the initial cloud foundation contracts.

This module prepares an execution review packet only. It does not execute tasks,
provision cloud capacity, persist leases, or claim real provider availability.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from brain_v12.brain.cloud_capacity_gate import CapacityRequest, evaluate_free_capacity
from brain_v12.brain.cloud_executor import BrainCloudExecutor, ExecutionRequest, ExecutorStatus
from brain_v12.brain.execution_evidence_bundle import build_evidence_bundle
from brain_v12.brain.execution_lease import issue_lease
from brain_v12.brain.resource_fabric import ResourceRecord, ResourceState
from brain_v12.brain.resource_health import HealthObservation, HealthState
from brain_v12.brain.task_envelope import TaskEnvelope
from brain_v12.brain.task_scheduler import ScheduleStatus, TaskRequest, select_resource


@dataclass(frozen=True)
class FoundationPreparation:
    status: str
    task_id: str
    resource_id: str | None
    reasons: tuple[str, ...]
    executor_status: str | None
    executed: bool
    evidence_bundle: Mapping[str, Any]


def prepare_execution_review(
    envelope: TaskEnvelope,
    *,
    capacity_request: CapacityRequest,
    capacity_evidence: Mapping[str, Any],
    resources: Sequence[ResourceRecord],
    health_observations: Mapping[str, HealthObservation],
    executor_id: str,
    fencing_token: int,
    now: datetime | None = None,
    lease_ttl_seconds: float = 60.0,
    identity_verified: bool = False,
    permission_granted: bool = False,
    executor: BrainCloudExecutor | None = None,
) -> FoundationPreparation:
    """Validate contracts and prepare a review-only receipt, failing closed."""
    instant = now or datetime.now(timezone.utc)
    if instant.tzinfo is None or instant.utcoffset() is None:
        return _blocked(envelope.task_id, ("CURRENT_TIME_MUST_BE_TIMEZONE_AWARE",), instant)
    instant = instant.astimezone(timezone.utc)

    reasons = list(envelope.validate())
    gate = evaluate_free_capacity(capacity_request, capacity_evidence, now=instant)
    if not gate["eligible"]:
        reasons.extend(f"CLOUD_CAPACITY:{reason}" for reason in gate["blocked_reasons"])

    if reasons:
        return _blocked(envelope.task_id, tuple(reasons), instant)

    healthy_resources: list[ResourceRecord] = []
    for resource in resources:
        observation = health_observations.get(resource.resource_id)
        if observation is None or observation.resource_id != resource.resource_id:
            continue
        if observation.classify() != HealthState.HEALTHY:
            continue
        if resource.state != ResourceState.AVAILABLE:
            continue
        healthy_resources.append(resource)

    decision = select_resource(
        TaskRequest(
            envelope.task_id,
            capacity_request.vcpu,
            capacity_request.memory_mb,
            capacity_request.storage_gb,
        ),
        healthy_resources,
    )
    if decision.status != ScheduleStatus.SELECTED or not decision.resource_id:
        return _blocked(envelope.task_id, (f"SCHEDULER:{decision.reason}",), instant)

    try:
        lease = issue_lease(
            envelope.task_id,
            executor_id,
            fencing_token,
            instant.timestamp(),
            lease_ttl_seconds,
        )
    except (TypeError, ValueError):
        return _blocked(envelope.task_id, ("EXECUTION_LEASE_INVALID",), instant)

    if lease.validate(instant.timestamp()).value != "VALID":
        return _blocked(envelope.task_id, ("EXECUTION_LEASE_NOT_VALID",), instant)

    executor_impl = executor or BrainCloudExecutor(executor_id=executor_id)
    receipt = executor_impl.submit(
        ExecutionRequest(
            task_id=envelope.task_id,
            resource_id=decision.resource_id,
            operation=str(envelope.payload.get("operation", "unspecified")),
            intent_hash=envelope.intent_hash,
            max_cost_usd=envelope.max_cost_usd,
        ),
        identity_verified=identity_verified,
        resource_available=True,
        permission_granted=permission_granted,
        cost_verified_zero=gate["eligible"] and envelope.max_cost_usd == "0",
    )
    status = (
        "PREPARED_NOT_EXECUTED"
        if receipt.status == ExecutorStatus.ACCEPTED_FOR_REVIEW and not receipt.executed
        else "BLOCKED"
    )
    reasons_out = () if status == "PREPARED_NOT_EXECUTED" else (receipt.reason,)
    bundle = build_evidence_bundle(
        envelope.task_id,
        status,
        instant.isoformat(),
        {
            "resource_id": decision.resource_id,
            "scheduler_status": decision.status.value,
            "lease_id": lease.lease_id,
            "lease_status": lease.validate(instant.timestamp()).value,
            "executor_status": receipt.status.value,
            "executor_reason": receipt.reason,
            "execution_performed": False,
            "capacity_gate_eligible": gate["eligible"],
            "capacity_evidence_source_ref": gate.get("evidence_source_ref"),
            "capacity_evidence_provider": gate.get("provider"),
        },
    )
    return FoundationPreparation(
        status=status,
        task_id=envelope.task_id,
        resource_id=decision.resource_id if status == "PREPARED_NOT_EXECUTED" else None,
        reasons=reasons_out,
        executor_status=receipt.status.value,
        executed=False,
        evidence_bundle=bundle,
    )


def _blocked(task_id: str, reasons: tuple[str, ...], now: datetime) -> FoundationPreparation:
    safe_now = now if now.tzinfo is not None and now.utcoffset() is not None else now.replace(tzinfo=timezone.utc)
    bundle = build_evidence_bundle(
        task_id or "invalid-task",
        "BLOCKED",
        safe_now.isoformat(),
        {"reasons": list(reasons), "execution_performed": False},
    )
    return FoundationPreparation(
        status="BLOCKED",
        task_id=task_id,
        resource_id=None,
        reasons=reasons,
        executor_status=None,
        executed=False,
        evidence_bundle=bundle,
    )
