from datetime import datetime, timedelta, timezone

from brain_v12.brain.cloud_capacity_gate import CapacityRequest
from brain_v12.brain.cloud_foundation_coordinator import prepare_execution_review
from brain_v12.brain.resource_fabric import ResourceRecord, ResourceState
from brain_v12.brain.resource_health import HealthObservation


NOW = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)


def make_envelope():
    from brain_v12.brain.task_envelope import TaskEnvelope

    return TaskEnvelope(
        1, "coordinator-task", "idem-coordinator-task", "sha256:test-intent",
        ("local.test",), "test-only", "0", {"operation": "noop"},
    )


def make_capacity_evidence(**overrides):
    evidence = {
        "provider_verified": True,
        "provider": "unit-test-provider",
        "region": "unit-test-region",
        "sku": "unit-test-sku",
        "source_ref": "unit-test-fixture-not-real-provider-evidence",
        "observed_at": (NOW - timedelta(seconds=1)).isoformat(),
        "expires_at": (NOW + timedelta(minutes=1)).isoformat(),
        "free_tier_eligible": True,
        "estimated_monthly_cost_usd": "0",
        "available_vcpu": 2,
        "available_memory_mb": 2048,
        "available_storage_gb": 10,
    }
    evidence.update(overrides)
    return evidence


def make_resource():
    return ResourceRecord(
        "local-test", "local", "unit-test", ResourceState.AVAILABLE,
        vcpu=2, memory_mb=2048, storage_gb=10,
    )


def test_coordinator_prepares_review_only_and_never_claims_execution():
    result = prepare_execution_review(
        make_envelope(),
        capacity_request=CapacityRequest(1, 512, 1),
        capacity_evidence=make_capacity_evidence(),
        resources=[make_resource()],
        health_observations={
            "local-test": HealthObservation("local-test", NOW.timestamp(), NOW.timestamp(), 30)
        },
        executor_id="unit-test-executor",
        fencing_token=1,
        now=NOW,
        identity_verified=True,
        permission_granted=True,
    )
    assert result.status == "PREPARED_NOT_EXECUTED"
    assert result.resource_id == "local-test"
    assert result.executed is False
    assert result.evidence_bundle["execution_verified"] is False
    assert result.evidence_bundle["bundle"]["evidence"]["execution_performed"] is False


def test_coordinator_blocks_stale_resource():
    result = prepare_execution_review(
        make_envelope(),
        capacity_request=CapacityRequest(1, 512, 1),
        capacity_evidence=make_capacity_evidence(),
        resources=[make_resource()],
        health_observations={
            "local-test": HealthObservation("local-test", NOW.timestamp() - 100, NOW.timestamp(), 5)
        },
        executor_id="unit-test-executor",
        fencing_token=1,
        now=NOW,
        identity_verified=True,
        permission_granted=True,
    )
    assert result.status == "BLOCKED"
    assert result.resource_id is None
    assert result.executed is False
    assert any(reason.startswith("SCHEDULER:") for reason in result.reasons)


def test_coordinator_blocks_nonzero_cloud_cost():
    result = prepare_execution_review(
        make_envelope(),
        capacity_request=CapacityRequest(1, 512, 1),
        capacity_evidence=make_capacity_evidence(estimated_monthly_cost_usd="0.01"),
        resources=[make_resource()],
        health_observations={
            "local-test": HealthObservation("local-test", NOW.timestamp(), NOW.timestamp(), 30)
        },
        executor_id="unit-test-executor",
        fencing_token=1,
        now=NOW,
        identity_verified=True,
        permission_granted=True,
    )
    assert result.status == "BLOCKED"
    assert result.resource_id is None
    assert any("zero_cost_confirmed" in reason for reason in result.reasons)
