from .runtime import BrainCoreV2
from .world import MiniWorld

if __name__ == "__main__":
    world = MiniWorld(goal=4)
    brain = BrainCoreV2(world)
    print(brain.run(12))
