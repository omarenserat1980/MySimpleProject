from brain_v7.braincore_v2.reasoning_quality_controller import ReasoningQualityController


def test_quality_controller_flags_weak_evidence():
    q = ReasoningQualityController()
    report = q.evaluate(
        understanding_confidence=0.4,
        evidence_count=1,
        contradiction_count=2,
        alternative_count=1,
        reversibility=0.3,
    )
    assert report.overall < 0.6
    assert "seek_more_evidence" in report.recommendations


def test_quality_controller_accepts_multiple_reversible_options():
    q = ReasoningQualityController()
    report = q.evaluate(
        understanding_confidence=0.9,
        evidence_count=5,
        contradiction_count=0,
        alternative_count=3,
        reversibility=0.9,
    )
    assert report.overall > 0.8
