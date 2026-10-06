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

def test_deep_audit_uses_existing_income_lifecycle():
    class Income:
        def snapshot(self, client_id=None):
            assert client_id == "CL-000003"
            return {"verified_revenue_jod": 0, "opportunities": [{"status": "READY_TO_APPLY", "client_id": client_id}]}
    class Lifecycle:
        ORDER = ("DISCOVERY", "QUALIFIED", "READY_TO_APPLY", "SUBMITTED", "CLIENT_RESPONDED", "ACCEPTED", "DELIVERING", "COMPLETED", "PAYMENT_VERIFIED")
        def summary(self, client_id=None):
            assert client_id == "CL-000003"
            return {"counts": {"READY_TO_APPLY": 1}, "payment_verified_jod": 0, "client_id": client_id}
    guardian = ClientRevenueGuardian(
        activity_reader=lambda _id: {},
        revenue_reader=lambda _id: {"verified_revenue_jod": 0},
    )
    report = guardian.deep_inspect(Income(), Lifecycle())
    assert report["deep_audit"]["highest_priority"] == "CONVERT_READY_TO_APPLY_TO_SUBMITTED_WITH_EXTERNAL_EVIDENCE"
    assert report["deep_audit"]["hard_gate"] == "PAYMENT_VERIFIED + payment_evidence"


def test_deep_audit_enables_client_data_isolation():
    class Income:
        def snapshot(self, client_id=None):
            assert client_id == "CL-000003"
            return {"verified_revenue_jod": 0, "opportunities": []}
    class Lifecycle:
        ORDER = ("DISCOVERY", "PAYMENT_VERIFIED")
        def summary(self, client_id=None):
            assert client_id == "CL-000003"
            return {"counts": {}, "payment_verified_jod": 0, "client_id": client_id}
    guardian = ClientRevenueGuardian(
        activity_reader=lambda client_id: {"client_id": client_id},
        revenue_reader=lambda client_id: {"verified_revenue_jod": 0, "client_id": client_id},
    )
    report = guardian.deep_inspect(Income(), Lifecycle(), "CL-000003")
    assert report["deep_audit"]["client_data_isolation"] is True
    assert report["policy"]["client_data_isolation"] is True


def test_history_is_append_only_and_preserves_each_step():
    class Store:
        def __init__(self):
            self.records = []
        def revenue_guardian_checkpoint(self, client_id):
            if not self.records:
                return None
            return self.records[-1]
        def save_revenue_guardian_checkpoint(self, client_id, record):
            self.records.append(dict(record))
    store = Store()
    assert store.revenue_guardian_checkpoint("CL-000003") is None
    store.save_revenue_guardian_checkpoint("CL-000003", {"step": "BASELINE_CAPTURED", "current_verified_revenue_jod": 0})
    store.save_revenue_guardian_checkpoint("CL-000003", {"step": "REVENUE_UNCHANGED_REQUIRES_NEXT_STEP", "current_verified_revenue_jod": 0})
    store.save_revenue_guardian_checkpoint("CL-000003", {"step": "REVENUE_INCREASE_CONFIRMED", "current_verified_revenue_jod": 25})
    assert [x["step"] for x in store.records] == [
        "BASELINE_CAPTURED",
        "REVENUE_UNCHANGED_REQUIRES_NEXT_STEP",
        "REVENUE_INCREASE_CONFIRMED",
    ]
