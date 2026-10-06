from brain_v12.self_healing.request_driven_growth import RequestDrivenGrowth

def test_growth_is_request_driven(tmp_path):
    g = RequestDrivenGrowth(
        depth_controller=__import__(
            "brain_v12.self_healing.request_depth_controller",
            fromlist=["RequestDepthController"],
        ).RequestDepthController(tmp_path / "depth.json"),
        capability_planner=__import__(
            "brain_v12.self_healing.capability_evolution_planner",
            fromlist=["CapabilityEvolutionPlanner"],
        ).CapabilityEvolutionPlanner(tmp_path / "caps.json"),
    )
    first = g.plan("ابن تطبيق لفحص Azure")
    assert first.depth == 1
    assert "app" in first.new_capabilities
    assert "cloud" in first.new_capabilities
