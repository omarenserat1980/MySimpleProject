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


def test_deep_inspect_derives_bounded_recovery_action_on_decrease():
    class Income:
        def snapshot(self, client_id=None):
            return {"verified_revenue_jod": 80, "opportunities": []}
    class Lifecycle:
        ORDER = ("DISCOVERY", "PAYMENT_VERIFIED")
        def summary(self, client_id=None):
            return {"counts": {}, "payment_verified_jod": 80}
    saved = []
    guardian = ClientRevenueGuardian(
        activity_reader=lambda _id: {},
        revenue_reader=lambda _id: {"verified_revenue_jod": 80},
        progress_reader=lambda _id: {"verified_revenue_jod": 100},
        progress_writer=lambda _id, record: saved.append(record),
    )
    report = guardian.deep_inspect(Income(), Lifecycle())
    assert report["deep_audit"]["revenue_trend"] == "DECREASED"
    assert report["deep_audit"]["next_action"] == "RECOVER_ONE_REVENUE_PATH_BEFORE_ACCEPTING_NEW_WORK"
    assert report["deep_audit"]["escalation"] == "REVENUE_RECOVERY_ESCALATION"
    assert report["deep_audit"]["dispatch_allowed"] is False
    assert saved[-1]["action_constraint"] == "ONE_BOUNDED_ACTION_THROUGH_EXISTING_PRIMARY_PIPELINE"


def test_advance_once_requests_one_persisted_next_step():
    calls = []
    saved = []
    class Income:
        def snapshot(self, client_id=None):
            return {"verified_revenue_jod": 80, "opportunities": []}
    class Lifecycle:
        ORDER = ("DISCOVERY", "PAYMENT_VERIFIED")
        def summary(self, client_id=None):
            return {"counts": {}, "payment_verified_jod": 80}
    guardian = ClientRevenueGuardian(
        activity_reader=lambda _id: {},
        revenue_reader=lambda _id: {"verified_revenue_jod": 80},
        progress_reader=lambda _id: {"verified_revenue_jod": 100},
        progress_writer=lambda _id, record: saved.append(record),
        action_requester=lambda _id, action: calls.append(action) or {"accepted": True},
    )
    result = guardian.advance_once(Income(), Lifecycle())
    assert result["status"] == "NEXT_STEP_REQUESTED"
    assert len(calls) == 1
    assert calls[0]["next_action"] == "RECOVER_ONE_REVENUE_PATH_BEFORE_ACCEPTING_NEW_WORK"
    assert calls[0]["constraint"] == "ONE_BOUNDED_ACTION_THROUGH_EXISTING_PRIMARY_PIPELINE"
    assert saved[-1]["action_status"] == "REQUESTED"
    assert saved[-1]["dispatch_allowed"] is False


def test_advance_once_blocks_duplicate_without_new_measurement():
    calls = []
    class Income:
        def snapshot(self, client_id=None):
            return {"verified_revenue_jod": 80, "opportunities": []}
    class Lifecycle:
        ORDER = ("DISCOVERY", "PAYMENT_VERIFIED")
        def summary(self, client_id=None):
            return {"counts": {}, "payment_verified_jod": 80}
    guardian = ClientRevenueGuardian(
        activity_reader=lambda _id: {},
        revenue_reader=lambda _id: {"verified_revenue_jod": 80},
        progress_reader=lambda _id: {
            "current_verified_revenue_jod": 80,
            "verified_revenue_jod": 80,
            "action_status": "REQUESTED",
            "action_requested": "RECOVER_ONE_REVENUE_PATH_BEFORE_ACCEPTING_NEW_WORK",
        },
        progress_writer=lambda _id, _record: None,
        action_requester=lambda _id, action: calls.append(action) or {"accepted": True},
    )
    result = guardian.advance_once(Income(), Lifecycle())
    assert result["status"] == "WAITING_FOR_RECHECK"
    assert result["action_requested"] is False
    assert calls == []


def test_first_revenue_mission_accepts_live_url_field():
    class Income:
        def snapshot(self, client_id=None):
            return {
                "verified_revenue_jod": 0,
                "opportunities": [{
                    "opportunity_id": "LIVE-URL-1",
                    "status": "READY_TO_APPLY",
                    "score": 92,
                    "data": {
                        "title": "Python API integration",
                        "url": "https://example.com/projects/1",
                        "requirements": "Integrate a Python REST API",
                        "evidence": "Public listing evidence",
                    },
                }],
            }

    class Lifecycle:
        ORDER = ("DISCOVERY", "QUALIFIED", "READY_TO_APPLY", "SUBMITTED", "COMPLETED", "PAYMENT_VERIFIED")
        def summary(self, client_id=None):
            return {"counts": {"READY_TO_APPLY": 1}, "payment_verified_jod": 0}

    saved = []
    guardian = ClientRevenueGuardian(
        activity_reader=lambda _id: {},
        revenue_reader=lambda _id: {"verified_revenue_jod": 0},
        progress_reader=lambda _id: {},
        progress_writer=lambda _id, record: saved.append(record),
    )
    result = guardian.first_revenue_mission(Income(), Lifecycle())
    mission = result["mission"]
    assert result["status"] == "FIRST_REVENUE_MISSION_CREATED"
    assert mission["selected_opportunity_url"] == "https://example.com/projects/1"
    assert mission["selected_opportunity_quality"] is True
    assert saved[-1]["dispatch_allowed"] is False


# The revenue-conversion workflow invokes this module with unittest, while the
# assertions above are written as pytest-style functions. Expose wrappers so
# unittest actually executes the tests instead of reporting "Ran 0 tests".
import unittest


class ClientRevenueGuardianUnittestAdapter(unittest.TestCase):
    def test_registry_targets_cl_000003(self):
        test_registry_targets_cl_000003()

    def test_no_verified_revenue_is_not_reported_as_revenue(self):
        test_no_verified_revenue_is_not_reported_as_revenue()

    def test_blocker_has_priority_over_activity(self):
        test_blocker_has_priority_over_activity()

    def test_verified_revenue_stops_nudge(self):
        test_verified_revenue_stops_nudge()

    def test_nudge_is_single_bounded_request(self):
        test_nudge_is_single_bounded_request()

    def test_deep_audit_uses_existing_income_lifecycle(self):
        test_deep_audit_uses_existing_income_lifecycle()

    def test_deep_audit_enables_client_data_isolation(self):
        test_deep_audit_enables_client_data_isolation()

    def test_history_is_append_only_and_preserves_each_step(self):
        test_history_is_append_only_and_preserves_each_step()

    def test_deep_inspect_derives_bounded_recovery_action_on_decrease(self):
        test_deep_inspect_derives_bounded_recovery_action_on_decrease()

    def test_advance_once_requests_one_persisted_next_step(self):
        test_advance_once_requests_one_persisted_next_step()

    def test_advance_once_blocks_duplicate_without_new_measurement(self):
        test_advance_once_blocks_duplicate_without_new_measurement()

    def test_first_revenue_mission_accepts_live_url_field(self):
        test_first_revenue_mission_accepts_live_url_field()
