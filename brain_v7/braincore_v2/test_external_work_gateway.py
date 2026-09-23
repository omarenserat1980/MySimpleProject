"""Smoke tests for the permission-gated external work gateway."""
from brain_v7.braincore_v2.brain_orchestrator import UnifiedBrain


def test_external_work_lifecycle() -> None:
    brain = UnifiedBrain()
    gateway = brain.external_work

    account = gateway.register_account(
        "UPWORK",
        "primary",
        identity_verified=True,
        connector_enabled=False,
        permission_scope="READ_AND_DRAFT",
    )
    assert account["status"] == "ACTIVE"

    opportunity = gateway.ingest_opportunity(
        "UPWORK",
        "Arabic video editing",
        "Create a short cinematic promotional video.",
        skills=["MEDIA", "video"],
        budget_jod=80,
    )
    routed = gateway.route_opportunity(opportunity["opportunity_id"])
    assert routed["employee_id"] in brain.organization.employees

    proposal = gateway.draft_proposal(opportunity["opportunity_id"])
    assert proposal["requires_user_approval"] is True

    order = gateway.record_order(opportunity["opportunity_id"], 80)
    gateway.verify_payment(order["order_id"], 80, "platform_transaction:TEST-001")
    assert gateway.verified_revenue_jod() == 80


def test_gateway_never_accepts_strong_permission_scope() -> None:
    brain = UnifiedBrain()
    try:
        brain.external_work.register_account(
            "FIVERR", "primary", permission_scope="FULL_ACCESS"
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Unsafe permission scope was accepted")
