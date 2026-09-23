from brain_v7.braincore_v2.autonomy_controller import build_plan
def test_control_plan_has_safety_and_capability_sections():
    result=build_plan("test")
    assert "policy" in result and "capabilities" in result
    assert result["policy"]["autonomous_money_movement"] is False
