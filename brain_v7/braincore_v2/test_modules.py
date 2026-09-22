from .runtime import BrainCoreV2
from .world import MiniWorld

def test_workspace_and_routing():
    brain=BrainCoreV2(MiniWorld(goal=2)); d=brain.deliberate()
    assert d["association"]["routed_to"] in {"somatosensory","association","workspace"}
    assert brain.workspace.current is not None

def test_brain_reaches_goal_with_modulation():
    world=MiniWorld(goal=3); brain=BrainCoreV2(world); result=brain.run(10)
    assert world.state.position==3
    assert result["self_state"]["prediction_error"]>=0
