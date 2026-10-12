"""Durable evidence-backed marketing memory primitives."""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json

@dataclass(frozen=True)
class MarketingObservation:
    observation_id: str
    domain: str
    hypothesis: str
    metric: str
    outcome: float
    source: str
    confidence: float

    def fingerprint(self) -> str:
        payload=self.__dict__
        return sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def accept_observation(observation: MarketingObservation) -> bool:
    if not observation.observation_id or not observation.domain or not observation.hypothesis:
        return False
    if not 0 <= observation.confidence <= 1:
        return False
    return bool(observation.source and observation.metric)
