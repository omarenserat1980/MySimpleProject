from dataclasses import dataclass
from collections import deque

@dataclass
class Episode:
    observation: dict
    action: str
    outcome: dict

class HippocampalMemory:
    def __init__(self, capacity: int = 500):
        self.episodes = deque(maxlen=capacity)

    def encode(self, observation: dict, action: str, outcome: dict):
        importance = abs(float(outcome.get("reward", 0))) + float(outcome.get("risk", 0))
        if importance > 0.15 or outcome.get("reached"):
            self.episodes.append(Episode(observation.copy(), action, outcome.copy()))

    def recall(self, position: int, action: str | None = None) -> list[Episode]:
        return [e for e in reversed(self.episodes)
                if e.observation.get("position") == position and (action is None or e.action == action)]

    def predict_from_memory(self, position: int, action: str) -> dict | None:
        matches = self.recall(position, action)
        if not matches: return None
        e = matches[0]
        return {"to": e.outcome.get("to"), "reward": e.outcome.get("reward", 0),
                "risk": e.outcome.get("risk", 0), "confidence": 0.75}
