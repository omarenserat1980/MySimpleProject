from cloud.brain_interview import conduct_interview

def test_interview_is_operational_and_evidence_grounded():
    report = conduct_interview()
    assert report["identity"] == "Brain Cloud software system"
    assert len(report["answers"]) == 10
    assert report["literal_human_desire_claim"] is False
    assert report["literal_human_consciousness_claim"] is False
    assert "external_benchmark_adapters_not_configured" in report["blockers"]
    assert all(answer["evidence"] for answer in report["answers"])
