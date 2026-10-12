from brain_v12.self_healing.capability_evolution_planner import CapabilityEvolutionPlanner

def test_only_requested_capabilities_are_planned(tmp_path):
    p = CapabilityEvolutionPlanner(tmp_path / "caps.json")
    plan = p.plan("ابن تطبيق", ["app"], 4)
    assert plan["new_capability_delta"] == ["app"]
    assert plan["actions"][0]["action"] == "create_or_extend_application"
    assert plan["no_op_for_unused_capabilities"] is True

def test_existing_capability_has_no_duplicate_build(tmp_path):
    p = CapabilityEvolutionPlanner(tmp_path / "caps.json")
    p.record(p.plan("اكتب سكربت", ["script"], 1))
    plan = p.plan("اكتب سكربت آخر", ["script"], 2)
    assert plan["new_capability_delta"] == []
