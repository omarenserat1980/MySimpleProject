"""Internal cognitive delegation: compare specialist proposals before commitment."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

@dataclass
class Proposal:
    employee_id: str
    role: str
    proposal: str
    confidence: float
    evidence: int
    reversible: float

class CognitiveWorkforce:
    def __init__(self):
        self.last_review: dict = {}

    def review(self, objective: str, specialists: Iterable[dict]) -> dict:
        proposals = []
        for item in specialists:
            proposals.append(Proposal(
                employee_id=str(item.get("employee_id", "unknown")),
                role=str(item.get("role", "specialist")),
                proposal=str(item.get("proposal", "")),
                confidence=max(0.0, min(1.0, float(item.get("confidence", 0.0)))),
                evidence=max(0, int(item.get("evidence", 0))),
                reversible=max(0.0, min(1.0, float(item.get("reversible", 0.0)))),
            ))
        ranked = sorted(
            proposals,
            key=lambda p: (0.45*p.confidence + 0.30*min(1.0,p.evidence/3) + 0.25*p.reversible),
            reverse=True,
        )
        self.last_review = {
            "objective": objective,
            "selected": asdict(ranked[0]) if ranked else None,
            "alternatives": [asdict(p) for p in ranked[1:]],
            "proposal_count": len(ranked),
            "requires_external_approval": True,
        }
        return self.last_review

    def snapshot(self) -> dict:
        return dict(self.last_review)