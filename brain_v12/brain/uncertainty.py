"""Uncertainty and contradiction analysis for Brain V13."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Belief:
    value: Any
    confidence: float
    status: str


class UncertaintyEngine:
    def classify(self, *, value: Any = None, evidence_count: int = 0,
                 confidence: float = 0.0, contradicted: bool = False) -> Belief:
        if contradicted:
            status = "CONTRADICTED"
        elif evidence_count <= 0:
            status = "UNKNOWN"
        elif confidence >= 0.90:
            status = "KNOWN"
        elif confidence >= 0.60:
            status = "LIKELY"
        else:
            status = "UNCERTAIN"
        return Belief(value, max(0.0, min(1.0, confidence)), status)

    def resolve(self, observations: list[dict[str, Any]]) -> Belief:
        if not observations:
            return self.classify()
        values = {repr(o.get("value")) for o in observations}
        if len(values) > 1:
            return self.classify(value=observations[-1].get("value"),
                                 evidence_count=len(observations),
                                 confidence=min(float(o.get("confidence", 0.0)) for o in observations),
                                 contradicted=True)
        confidence = max(float(o.get("confidence", 0.0)) for o in observations)
        return self.classify(value=observations[-1].get("value"),
                             evidence_count=len(observations), confidence=confidence)
