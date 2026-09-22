class BasalGangliaSelector:
    def score(self, action: str, observation: dict, prediction: dict, goal_alignment: float) -> float:
        risk = float(prediction.get("risk", 0))
        reward = float(prediction.get("reward", 0))
        confidence = float(prediction.get("confidence", 0))
        return goal_alignment + reward + confidence - risk * 2.0 - (0.05 if action == "WAIT" else 0)

    def select(self, candidates: list[dict], threshold: float = -999) -> dict | None:
        ranked = sorted(candidates, key=lambda x: x["value"], reverse=True)
        if not ranked or ranked[0]["value"] < threshold: return None
        return ranked[0]

class InhibitoryController:
    def gate(self, candidate: dict | None, uncertainty: float, risk: float) -> dict:
        if candidate is None: return {"commit": False, "reason": "NO_CANDIDATE"}
        if risk > 0.8 or uncertainty > 0.9:
            return {"commit": False, "reason": "HIGH_RISK_OR_UNCERTAINTY"}
        return {"commit": True, "reason": "THRESHOLD_PASSED"}
