"""Reality Core: canonical, evidence-aware world state for Brain V13.

The core distinguishes facts, beliefs, assumptions and unknowns. It is deliberately
side-effect free so the orchestrator remains the single authority for execution.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum
import time
from typing import Any


class KnowledgeKind(str, Enum):
    FACT = "FACT"
    BELIEF = "BELIEF"
    ASSUMPTION = "ASSUMPTION"
    UNKNOWN = "UNKNOWN"
    CONTRADICTED = "CONTRADICTED"


@dataclass(frozen=True)
class Observation:
    key: str
    value: Any
    kind: KnowledgeKind = KnowledgeKind.FACT
    source: str = "brain"
    confidence: float = 1.0
    observed_at: float = field(default_factory=time.time)
    evidence_ids: tuple[str, ...] = ()

    def normalized_confidence(self) -> float:
        return max(0.0, min(1.0, float(self.confidence)))


class RealityCore:
    """Small canonical state store used by missions and verifiers."""

    def __init__(self) -> None:
        self._observations: dict[str, list[Observation]] = {}

    def observe(self, observation: Observation) -> Observation:
        self._observations.setdefault(observation.key, []).append(observation)
        return observation

    def get(self, key: str) -> Observation | None:
        items = self._observations.get(key, [])
        return items[-1] if items else None

    def history(self, key: str) -> list[Observation]:
        return list(self._observations.get(key, []))

    def resolve(self, key: str) -> Observation | None:
        items = self._observations.get(key, [])
        if not items:
            return None
        values = {repr(x.value) for x in items[-8:]}
        if len(values) > 1:
            latest = items[-1]
            return Observation(key, latest.value, KnowledgeKind.CONTRADICTED,
                               latest.source, latest.confidence, latest.observed_at,
                               latest.evidence_ids)
        return items[-1]

    def snapshot(self) -> dict[str, Any]:
        return {
            key: asdict(obs[-1])
            for key, obs in self._observations.items()
            if obs
        }

    def contradictions(self) -> list[str]:
        return [key for key in self._observations if self.resolve(key)
                and self.resolve(key).kind == KnowledgeKind.CONTRADICTED]
