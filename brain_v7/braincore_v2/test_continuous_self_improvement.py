from brain_v7.braincore_v2.continuous_self_improvement import ContinuousSelfImprovement


def test_loop_selects_improvement_from_quality_signals():
    loop = ContinuousSelfImprovement()
    item = loop.plan(
        objective="improve reasoning",
        recommendations=["seek_more_evidence"],
        quality=0.4,
        evidence=["low evidence coverage"],
    )
    assert item["selected_action"] == "improve_reliability"
    assert item["status"] == "PLANNED"


def test_loop_records_completion():
    loop = ContinuousSelfImprovement()
    item = loop.plan(objective="add regression coverage", quality=0.9)
    done = loop.complete(item["cycle_id"], status="VALIDATED", result={"tests": "PASS"})
    assert done["status"] == "VALIDATED"
    assert done["result"]["tests"] == "PASS"


def test_policy_blocks_dangerous_side_effects():
    loop = ContinuousSelfImprovement()
    policy = loop.snapshot()["policy"]
    assert policy["shell_execution"] is False
    assert policy["credential_access"] is False
    assert policy["money_movement"] is False
    assert policy["arbitrary_deletion"] is False
