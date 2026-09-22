"""Controller that closes the autonomous predict-act-observe-learn loop."""
from .adaptive_learning import AdaptiveLearning

class AutonomousController:
    def __init__(self, loop):
        self.loop = loop
        self.learning = AdaptiveLearning()
        self.cycle = 0

    def step(self, state: dict):
        self.cycle += 1
        actions = state.get("actions") or [state.get("action", "inspect")]
        selected = self.learning.best_action(actions) or actions[0]

        expected = state.get("expected")
        if expected is not None:
            self.learning.remember_prediction(selected, expected)

        enriched = dict(state)
        enriched["action"] = selected
        result = self.loop.step(enriched)

        actual = result.get("result")
        experience = self.learning.learn(
            goal_id=result.get("goal_id", "unknown"),
            action=selected,
            expected=expected,
            actual=actual,
            cycle=self.cycle,
        )
        result["learning"] = {
            "error": experience.error,
            "reward": experience.reward,
            "lesson": experience.lesson,
        }
        return result

    def status(self):
        return {"cycle": self.cycle, "learning": self.learning.status()}
