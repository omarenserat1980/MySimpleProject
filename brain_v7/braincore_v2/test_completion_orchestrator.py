from brain_v7.braincore_v2.completion_orchestrator import (
    build_default_readiness_snapshot,
    evaluate,
)


def test_default_readiness_is_explicit_about_external_verification():
    report = evaluate(build_default_readiness_snapshot())
    assert report["status"] == "READY_WITH_EXTERNAL_VERIFICATION"
    assert report["revenue_is_guaranteed"] is False
    assert report["external_side_effects_claimed"] is False
    assert report["live_stages"] == ()
    assert report["blocked_stages"] == ()


def test_missing_deployment_is_blocked():
    snapshot = build_default_readiness_snapshot()
    snapshot["deployment"] = {"configured": False}
    report = evaluate(snapshot)
    assert "S9" in report["blocked_stages"]
    assert report["status"] == "PARTIALLY_READY"
