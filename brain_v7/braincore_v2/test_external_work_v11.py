"""Regression tests for external-work safety and routing."""
from brain_v7.braincore_v2.brain_orchestrator import UnifiedBrain


def test_adapter_queue_and_metrics() -> None:
    brain = UnifiedBrain()
    g = brain.external_work
    g.register_account("UPWORK", "main", identity_verified=True)
    opp = g.ingest_opportunity(
        "UPWORK", "Video editing", "Short cinematic video",
        ["MEDIA", "video"], 80, "https://example.invalid/job/1"
    )
    assert g.queue.snapshot()["queued"] == 1
    routed = g.route_opportunity(opp["opportunity_id"])
    assert routed["employee_id"]
    assert g.adapters.get("UPWORK").platform == "UPWORK"
    assert g.metrics()["opportunities"] == 1


def test_compliance_blocks_dangerous_actions() -> None:
    brain = UnifiedBrain()
    for action in ("SPAM", "MONEY_TRANSFER", "FAKE_IDENTITY", "UNAUTHORIZED_ACCESS"):
        decision = brain.external_work.evaluate_action(action)
        assert decision["allowed"] is False


def test_submission_requires_authorization() -> None:
    brain = UnifiedBrain()
    decision = brain.external_work.evaluate_action("SUBMIT_PROPOSAL")
    assert decision["allowed"] is False
    assert decision["requires_user_approval"] is True
