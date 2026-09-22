class CerebellarPredictor:
    def __init__(self):
        self.model: dict[tuple[int, str], dict] = {}

    def predict(self, observation: dict, action: str) -> dict:
        key = (observation["position"], action)
        learned = self.model.get(key)
        if learned: return {**learned, "source": "learned"}
        pos = observation["position"]
        to = pos + (1 if action == "RIGHT" else -1 if action == "LEFT" else 0)
        to = max(0, min(observation["goal"], to))
        return {"to": to, "reward": 0.0, "risk": 0.0, "confidence": 0.25, "source": "prior"}

    def learn(self, observation: dict, action: str, outcome: dict) -> float:
        prediction = self.predict(observation, action)
        error = abs(float(prediction.get("to", 0)) - float(outcome.get("to", 0)))
        error += abs(float(prediction.get("reward", 0)) - float(outcome.get("reward", 0))) / 10.0
        self.model[(observation["position"], action)] = {
            "to": outcome.get("to"), "reward": outcome.get("reward", 0),
            "risk": outcome.get("risk", 0), "confidence": min(1.0, prediction.get("confidence", 0.25) + 0.15)
        }
        return error
