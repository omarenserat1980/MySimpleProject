from brain_v7.braincore_v2.brain_orchestrator import UnifiedBrain


def test_brain_exposes_continuous_self_improvement():
    brain = UnifiedBrain(initial_employees=8)
    result = brain.cycle("improve the reasoning engine")
    assert result["self_improvement_plan"]["status"] == "PLANNED"
    assert result["self_improvement"]["continuous_loop"] is True
    assert result["code_tool"]["interface"] == "BRAIN_CODE_TOOL"
