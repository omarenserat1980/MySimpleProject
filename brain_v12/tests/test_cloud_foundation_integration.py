"""Cross-component safety tests for the initial cloud foundation.

These tests exercise the contracts together without launching processes,
provisioning cloud resources, or claiming that a task was executed.
"""
from datetime import datetime, timedelta, timezone

from brain_v12.brain.cloud_capacity_gate import CapacityRequest, evaluate_free_capacity
from brain_v12.brain.cloud_executor import BrainCloudExecutor, ExecutionRequest, ExecutorStatus
from brain_v12.brain.execution_evidence_bundle import build_evidence_bundle
from brain_v12.brain.execution_lease import LeaseStatus, issue_lease
from brain_v12.brain.resource_fabric import ResourceRecord, ResourceState
from brain_v12.brain.resource_health import HealthObservation, HealthState
from brain_v12.brain.task_envelope import TaskEnvelope
from brain_v12.brain.task_scheduler import ScheduleStatus, TaskRequest, select_resource

NOW = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)


def test_foundation_contracts_compose_without_claiming_execution():
    envelope = TaskEnvelope(
        schema_version=1,
        task_id="integration-task-1",
        idempotency_key="idem-integration-task-1",
        intent_hash="sha256:integration-fixture",
        requested_capabilities=("local.test",),
        authorization_scope="test-only",
        max_cost_usd="0",
        payload={"operation": "noop"},
    )
    assert envelope.validate() == ()

    health = HealthObservation("local-test", NOW.timestamp(), NOW.timestamp(), 60)
    assert health.classify() == HealthState.HEALTHY

    resource = ResourceRecord(
        "local-test", "local", "test-fixture", ResourceState.AVAILABLE,
        vcpu=2, memory_mb=2048, storage_gb=10,
    )
    decision = select_resource(TaskRequest(envelope.task_id, 1, 512, 1), [resource])
    assert decision.status == ScheduleStatus.SELECTED
    assert decision.resource_id == resource.resource_id

    lease = issue_lease(envelope.task_id, "test-executor", 1, NOW.timestamp(), 60)
    assert lease.validate(NOW.timestamp() + 1) == LeaseStatus.VALID

    capacity_evidence = {
        "provider_verified": True,
        "provider": "test-fixture-only",
        "region": "test-region",
        "sku": "test-sku",
        "source_ref": "unit-test-fixture-not-provider-proof",
        "observed_at": (NOW - timedelta(seconds=1)).isoformat(),
        "expires_at": (NOW + timedelta(minutes=1)).isoformat(),
        "free_tier_eligible": True,
        "estimated_monthly_cost_usd": "0",
        "available_vcpu": 2,
        "available_memory_mb": 2048,
        "available_storage_gb": 10,
    }
    gate = evaluate_free_capacity(CapacityRequest(1, 512, 1), capacity_evidence, now=NOW)
    assert gate["eligible"] is True
    # A unit-test fixture is not evidence of real provider capacity.
    assert capacity_evidence["source_ref"].startswith("unit-test-fixture")

    receipt = BrainCloudExecutor().submit(
        ExecutionRequest(
            envelope.task_id, decision.resource_id, "noop",
            envelope.intent_hash, envelope.max_cost_usd,
        ),
        identity_verified=True,
        resource_available=True,
        permission_granted=True,
        cost_verified_zero=True,
    )
    assert receipt.status == ExecutorStatus.ACCEPTED_FOR_REVIEW
    assert receipt.executed is False
    assert receipt.reason == "PROTOTYPE_EXECUTION_DISABLED"

    evidence = build_evidence_bundle(
        envelope.task_id,
        "PREPARED_NOT_EXECUTED",
        NOW.isoformat(),
        {
            "schedule_status": decision.status.value,
            "lease_status": lease.validate(NOW.timestamp() + 1).value,
            "executor_status": receipt.status.value,
            "execution_performed": receipt.executed,
            "capacity_fixture_only": True,
        },
    )
    assert evidence["execution_verified"] is False
    assert evidence["signature_verified"] is False
    assert evidence["bundle"]["status"] == "PREPARED_NOT_EXECUTED"


def test_stale_resource_health_blocks_integration_path():
    health = HealthObservation("local-test", 10, 100, 5)
    assert health.classify() == HealthState.STALE
    # A stale resource must not be promoted to AVAILABLE by this integration
    # contract; the caller must withhold it from the scheduler.
    resource = ResourceRecord(
        "local-test", "local", "test-fixture", ResourceState.BLOCKED,
        vcpu=2, memory_mb=2048, storage_gb=10,
    )
    decision = select_resource(TaskRequest("stale-task"), [resource])
    assert decision.status == ScheduleStatus.NO_RESOURCE
    assert decision.resource_id is None
