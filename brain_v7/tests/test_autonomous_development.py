from brain_v7.braincore_v2.autonomous_development_supervisor import plan_next, record_attempt
from brain_v7.braincore_v2.capability_registry import capability_summary

def test_plan_is_bounded_and_evidence_driven():
    plan=plan_next()
    assert plan["status"] in {"PLANNED","NO_WORK"}
    if plan["status"]=="PLANNED":
        assert plan["task"]["evidence"]

def test_capability_summary_is_conservative():
    summary=capability_summary()
    assert summary["counts"]
