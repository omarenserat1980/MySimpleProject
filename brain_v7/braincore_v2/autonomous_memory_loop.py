"""Autonomous controller with world-model prediction and experience storage."""
from .experience_world import ExperienceWorld

class AutonomousMemoryLoop:
    def __init__(self, controller):
        self.controller = controller
        self.world = ExperienceWorld()
        self.last_state = None
        self.steps = 0

    def step(self, state: dict):
        self.steps += 1
        action = (self.controller.learning.best_action(state.get("actions", []))
                  or state.get("action", "inspect"))
        prediction = self.world.predict(state, action)

        enriched = dict(state)
        enriched["action"] = action
        if prediction is not None and "expected" not in enriched:
            enriched["expected"] = prediction["outcome"]

        result = self.controller.step(enriched)
        actual = result.get("result")
        reward = result.get("learning", {}).get("reward", 0.0)

        next_state = result.get("next_state", state)
        self.world.observe(state, action, next_state, actual, reward)
        self.last_state = next_state

        result["world_prediction"] = prediction
        result["world"] = self.world.status()
        return result

    def status(self):
        return {
            "steps": self.steps,
            "world": self.world.status(),
            "controller": self.controller.status(),
        }
