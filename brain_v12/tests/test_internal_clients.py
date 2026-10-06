from brain_v12.brain.internal_clients import INTERNAL_CLIENTS, launch_plan, resolve_internal_client


class FakeBridge:
    def __init__(self, online=True):
        self.online = online

    def status(self):
        return {"enabled": self.online, "agents": {"online": self.online}}


def test_active_customers_are_internal_clients():
    assert INTERNAL_CLIENTS["BRAIN-INTERNAL-CL-000001"]["customer_id"] == "CL-000001"
    assert INTERNAL_CLIENTS["BRAIN-INTERNAL-CL-000002"]["customer_id"] == "CL-000002"


def test_unknown_internal_client_fails_closed():
    assert resolve_internal_client("BRAIN-INTERNAL-CL-999999")["status"] == "UNKNOWN_INTERNAL_CLIENT"


def test_launch_plan_uses_existing_backend_and_pipeline_policy():
    result = launch_plan("BRAIN-INTERNAL-CL-000001", FakeBridge())
    assert result["status"] == "READY_TO_LAUNCH"
    assert result["plan"]["backend"] == "DEVICE_BRIDGE"
    assert result["execution_policy"] == "EXISTING_PRIMARY_PIPELINE"
    assert result["completion_policy"] == "VERIFY_AND_EVIDENCE_REQUIRED"


def test_revenue_guardian_is_supervisory_only():
    result = launch_plan("BRAIN-INTERNAL-CL-000004", FakeBridge())
    assert result["status"] == "SUPERVISORY_READY"
    assert result["client"]["customer_id"] == "CL-000003"
    assert result["plan"]["dispatch_allowed"] is False
    assert result["execution_policy"] == "SUPERVISORY_ONLY_EXISTING_PRIMARY_PIPELINE"
