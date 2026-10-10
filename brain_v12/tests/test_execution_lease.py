from brain_v12.brain.execution_lease import (
    ExecutionLease, LeaseStatus, issue_lease,
)


def test_lease_valid_before_expiry_and_expired_at_boundary():
    lease = issue_lease("task-1", "worker-1", 1, 100, 30)
    assert lease.validate(129.9) == LeaseStatus.VALID
    assert lease.validate(130) == LeaseStatus.EXPIRED


def test_invalid_lease_values_fail_closed():
    lease = ExecutionLease("", "task", "worker", 0, 100, 90)
    assert lease.validate(110) == LeaseStatus.INVALID


def test_issue_lease_rejects_bad_fencing_token():
    try:
        issue_lease("task", "worker", 0, 100, 10)
    except ValueError as exc:
        assert str(exc) == "FENCING_TOKEN_INVALID"
    else:
        raise AssertionError("invalid fencing token accepted")
