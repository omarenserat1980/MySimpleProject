from brain_v7.braincore_v2.brain_orchestrator import UnifiedBrain


def test_brain_exposes_adaptive_reasoning_and_control_plane():
    brain = UnifiedBrain(initial_employees=4)
    result = brain.cycle("طور الفهم والاستدلال والمرونة")
    assert "adaptive_reasoning" in result
    assert result["adaptive_reasoning"]["hypotheses"]
    assert "operational_control_plane" in result
    assert result["external_side_effects"] is False
    assert result["money_movement"] is False


def test_brain_keeps_reversible_alternatives():
    brain = UnifiedBrain(initial_employees=2)
    result = brain.cycle("improve the cognitive planner")
    labels = {h["label"] for h in result["adaptive_reasoning"]["hypotheses"]}
    assert "DECOMPOSE" in labels
    assert "EXPERIMENT" in labels
