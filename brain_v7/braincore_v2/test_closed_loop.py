from .runtime import BrainCoreV2
from .world import MiniWorld

def test_brain_reaches_goal():
    world = MiniWorld(goal=4)
    brain = BrainCoreV2(world)
    result = brain.run(12)
    assert world.state.position == 4
    assert any(x.get("outcome", {}).get("reached") for x in result["history"])

def test_learning_reduces_uncertainty():
    world = MiniWorld(goal=4)
    brain = BrainCoreV2(world)
    first = brain.deliberate()
    brain.step()
    second = brain.deliberate()
    assert second["selected"]["prediction"]["confidence"] >= first["selected"]["prediction"]["confidence"]
