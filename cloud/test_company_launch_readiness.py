from cloud.company_launch_readiness import classify


def test_release_allowed_without_commercial_evidence_is_needs_evidence():
    r = classify({"status": "RELEASE_ALLOWED"}, None)
    assert r.status == "NEEDS_EVIDENCE"
    assert r.release_allowed is True
    assert r.commercial_allowed is False


def test_blocked_release_is_blocked():
    r = classify({"status": "RELEASE_BLOCKED"}, None)
    assert r.status == "BLOCKED"
    assert r.release_allowed is False
    assert r.commercial_allowed is False


def test_verified_commercial_evidence_can_be_ready():
    r = classify(
        {"status": "RELEASE_ALLOWED"},
        {"customer": True, "delivery": True, "payment_verified": True},
    )
    assert r.status == "READY"
    assert r.release_allowed is True
    assert r.commercial_allowed is True
