"""Advanced, traceable decision engine for Electronic Brain V12."""
from dataclasses import dataclass, asdict
from typing import Any

@dataclass
class Candidate:
    id: str
    action: str
    expected: str
    risk: str = "low"
    requirements: list[str] | None = None
    reversible: bool = True
    evidence: list[str] | None = None
    confidence: float = 0.5

    def __post_init__(self):
        self.requirements = self.requirements or []
        self.evidence = self.evidence or []

class DecisionEngine:
    def __init__(self):
        self.history: list[dict[str, Any]] = []

    def generate(self, goal: str) -> list[dict[str, Any]]:
        g = goal.strip()
        candidates = [
            Candidate("observe", "جمع معلومات إضافية", "بيانات أوضح قبل التنفيذ", "low", ["information"], True, ["goal_text"], 0.70),
            Candidate("plan", "بناء خطة متعددة الخطوات", "خطة قابلة للتحقق", "low", ["planning"], True, ["goal_text"], 0.75),
            Candidate("act", "تنفيذ خطوة آمنة قابلة للعكس", "تقدم ملموس مع سجل تنفيذ", "medium", ["permission"], True, ["goal_text"], 0.60),
        ]
        return [asdict(c) for c in candidates]

    def choose(self, goal: str, options: list[dict[str, Any]], permissions: set[str] | None = None) -> dict[str, Any]:
        permissions = permissions or set()
        ranked = []
        for option in options:
            blocked = any(req not in permissions for req in option.get("requirements", []) if req == "permission")
            score = float(option.get("confidence", 0.5))
            if option.get("risk") == "high": score -= 0.35
            if not option.get("reversible", True): score -= 0.15
            if blocked: score = -1
            ranked.append((score, option, blocked))
        ranked.sort(key=lambda x: x[0], reverse=True)
        if not ranked or ranked[0][2]:
            result = {"status":"WAITING_APPROVAL","goal":goal,"options":options,"reason":"permission_required"}
        else:
            score, selected, _ = ranked[0]
            result = {"status":"DECIDED","goal":goal,"selected":selected,"score":round(score,3),
                      "reason":"traceable_heuristic","alternatives":[x[1] for x in ranked[1:]]}
        self.history.append(result)
        return result
