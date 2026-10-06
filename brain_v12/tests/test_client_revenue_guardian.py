from brain_v12.brain.client_revenue_guardian import (
    ClientRevenueGuardian,
    GUARDIAN_CLIENT_ID,
    TARGET_CLIENT_ID,
    public_guardian_registry,
)


def test_registry_targets_cl_000003():
    registry = public_guardian_registry()
    assert registry["guardian_client_id"] == GUARDIAN_CLIENT_ID
    assert registry["target_client_id"] == TARGET_CLIENT_ID == "CL-000003"
    assert registry["rules"]["verified_payment_only"] is True


def test_no_verified_revenue_is_not_reported_as_revenue():
    guardian = ClientRevenueGuardian(
        activity_reader=lambda _id: {"opportunity_count": 4, "completed_count": 1},
        revenue_reader=lambda _id: {"verified_revenue_jod": 0, "expected_value_jod": 500},
    )
    report = guardian.inspect()
    assert report["state"] == "ACTIVE_NO_VERIFIED_REVENUE"
    assert report["verified_revenue_jod"] == 0
    assert report["revenue_is_verified"] is False


def test_blocker_has_priority_over_activity():
    guardian = ClientRevenueGuardian(
        activity_reader=lambda _id: {"opportunity_count": 8},
        revenue_reader=lambda _id: {"verified_revenue_jod": 0},
        blocker_reader=lambda _id: [{"code": "NO_PAYMENT_PATH"}],
    )
    report = guardian.inspect()
    assert report["state"] == "BLOCKED_BEFORE_REVENUE"
    assert report["recommendation"]["action"] == "REMOVE_FIRST_BLOCKER"


def test_verified_revenue_stops_nudge():
    calls = []
    guardian = ClientRevenueGuardian(
        activity_reader=lambda _id: {"completed_count": 2},
        revenue_reader=lambda _id: {"verified_revenue_jod": 25},
        action_requester=lambda _id, action: calls.append(action),
    )
    report = guardian.nudge_once()
    assert report["status"] == "NO_NUDGE_REQUIRED"
    assert calls == []


def test_nudge_is_single_bounded_request():
    calls = []
    guardian = ClientRevenueGuardian(
        activity_reader=lambda _id: {"opportunity_count": 2},
        revenue_reader=lambda _id: {"verified_revenue_jod": 0},
        action_requester=lambda _id, action: calls.append(action) or {"accepted": True},
    )
    report = guardian.nudge_once()
    assert report["status"] == "NUDGE_REQUESTED"
    assert len(calls) == 1
    assert calls[0]["client_id"] == "CL-000003"
    assert calls[0]["constraint"] == "ONE_BOUNDED_ACTION_THROUGH_EXISTING_PRIMARY_PIPELINE"
