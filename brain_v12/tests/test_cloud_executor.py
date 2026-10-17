from brain_v12.brain.cloud_executor import (
    BrainCloudExecutor, ExecutionRequest, ExecutorStatus,
)


def test_executor_blocks_without_explicit_evidence_and_never_runs():
    receipt = BrainCloudExecutor().submit(ExecutionRequest("t1", "r1", "noop", "hash"))
    assert receipt.status == ExecutorStatus.BLOCKED
    assert receipt.executed is False
    assert "IDENTITY_NOT_VERIFIED" in receipt.reason


def test_even_approved_prototype_request_is_not_executed():
    receipt = BrainCloudExecutor().submit(
        ExecutionRequest("t2", "r2", "noop", "hash", "0"),
        identity_verified=True,
        resource_available=True,
        permission_granted=True,
        cost_verified_zero=True,
    )
    assert receipt.status == ExecutorStatus.ACCEPTED_FOR_REVIEW
    assert receipt.executed is False
    assert receipt.reason == "PROTOTYPE_EXECUTION_DISABLED"


def test_nonzero_cost_is_blocked():
    receipt = BrainCloudExecutor().submit(
        ExecutionRequest("t3", "r3", "noop", "hash", "0.01"),
        identity_verified=True, resource_available=True,
        permission_granted=True, cost_verified_zero=True,
    )
    assert receipt.status == ExecutorStatus.BLOCKED
    assert "NONZERO_COST_NOT_ALLOWED" in receipt.reason
