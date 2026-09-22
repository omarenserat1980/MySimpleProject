"""Outcome-driven learning layer for the autonomous loop."""
from dataclasses import dataclass, field
from typing import Any

@dataclass
class Experience:
    goal_id: str
    action: str
    expected: Any
    actual: Any
    error: float
    reward: float
    lesson: str
    cycle: int

class AdaptiveLearning:
    def __init__(self):
        self.experiences: list[Experience] = []
        self.action_values: dict[str, float] = {}
        self.predictions: dict[str, Any] = {}

    @staticmethod
    def error(expected: Any, actual: Any) -> float:
        if expected == actual:
            return 0.0
        if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
            scale = max(1.0, abs(float(expected)))
            return min(1.0, abs(float(actual) - float(expected)) / scale)
        return 1.0

    def learn(self, *, goal_id: str, action: str, expected: Any,
               actual: Any, cycle: int) -> Experience:
        err = self.error(expected, actual)
        reward = 1.0 - err
        old = self.action_values.get(action, 0.0)
        self.action_values[action] = old + 0.2 * (reward - old)
        lesson = "success" if err == 0 else ("partial_success" if err < 0.5 else "needs_revision")
        exp = Experience(goal_id, action, expected, actual, err, reward, lesson, cycle)
        self.experiences.append(exp)
        return exp

    def predict(self, action: str) -> Any:
        return self.predictions.get(action)

    def remember_prediction(self, action: str, expected: Any):
        self.predictions[action] = expected

    def best_action(self, actions: list[str]) -> str | None:
        return max(actions, key=lambda a: self.action_values.get(a, 0.0), default=None)

    def status(self):
        return {
            "experiences": len(self.experiences),
            "learned_actions": len(self.action_values),
            "predictions": len(self.predictions),
            "action_values": dict(self.action_values),
        }
