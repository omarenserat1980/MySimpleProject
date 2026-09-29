"""Behavioral heart layer for Brain Cloud.

Inspired by Quranic descriptions of qalb/qulub/fu'ad. This is not a literal
spiritual heart and does not issue religious rulings.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from .quran_heart_corpus import CORE_HEART_FUNCTIONS

@dataclass
class HeartState:
    openness: float = 0.5
    clarity: float = 0.5
    tranquility: float = 0.5
    compassion: float = 0.5
    integrity: float = 0.5
    coherence: float = 0.5
    uncertainty: float = 0.5
    rigidity: float = 0.0
    fear: float = 0.0
    doubt: float = 0.0

class HeartEngine:
    """Maintain an auditable internal-state model used for decision quality."""

    def __init__(self):
        self.state = HeartState()
        self.events: list[dict] = []

    @staticmethod
    def _clamp(v: float) -> float:
        return max(0.0, min(1.0, float(v)))

    def perceive(self, *, evidence: float, ambiguity: float, pressure: float,
                 social_impact: float) -> HeartState:
        evidence, ambiguity = self._clamp(evidence), self._clamp(ambiguity)
        pressure, social_impact = self._clamp(pressure), self._clamp(social_impact)
        self.state.openness = self._clamp(0.55*self.state.openness + 0.45*evidence - 0.25*pressure)
        self.state.clarity = self._clamp(0.55*self.state.clarity + 0.45*evidence - 0.35*ambiguity)
        self.state.uncertainty = self._clamp(0.45*self.state.uncertainty + 0.55*ambiguity)
        self.state.fear = self._clamp(0.45*self.state.fear + 0.55*pressure)
        self.state.compassion = self._clamp(0.65*self.state.compassion + 0.35*social_impact)
        self.state.tranquility = self._clamp(
            0.5*self.state.tranquility + 0.25*self.state.clarity
            + 0.25*self.state.coherence - 0.30*self.state.fear
        )
        self.events.append({"type":"perceive","state":asdict(self.state)})
        return self.state

    def review(self, *, contradiction: float = 0.0, new_evidence: float = 0.0) -> dict:
        contradiction, new_evidence = self._clamp(contradiction), self._clamp(new_evidence)
        self.state.rigidity = self._clamp(
            0.55*self.state.rigidity + 0.35*contradiction - 0.30*new_evidence
        )
        self.state.coherence = self._clamp(
            0.65*self.state.coherence + 0.35*(1.0-contradiction)
        )
        action = "OPEN_TO_REVIEW" if self.state.rigidity < 0.55 else "FORCE_REVIEW"
        result = {
            "action": action,
            "state": asdict(self.state),
            "functions": CORE_HEART_FUNCTIONS,
            "literal_spiritual_heart_created": False,
        }
        self.events.append({"type":"review", **result})
        return result

    def audit(self) -> dict:
        return {
            "state": asdict(self.state),
            "events": list(self.events),
            "literal_spiritual_heart_created": False,
        }
