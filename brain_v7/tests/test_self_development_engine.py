from brain_v7.braincore_v2.self_development_engine import assess, next_development


def test_development_assessment_is_conservative():
    report = assess()
    assert report["evidence_gap_count"] > 0
    assert report["implemented_base_count"] >= 1


def test_next_development_requires_evidence():
    result = next_development()
    assert result["status"] in {"READY", "NO_PENDING_DOMAIN"}
    if result["status"] == "READY":
        assert result["next"]["status"] == "NEEDS_EVIDENCE"
