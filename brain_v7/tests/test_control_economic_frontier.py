from brain_v7.braincore_v2.autonomy_controller import build_plan

def test_control_plan_has_dependency_and_economic_frontiers():
    result=build_plan()
    plan=result["plan"]
    assert "economic_frontier" in plan
    assert len(plan["economic_frontier"]) >= 1
    assert "dependency_frontier" in result["capabilities"]
    assert result["policy"]["autonomous_money_movement"] is False
