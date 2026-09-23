"""Unified cognitive ecosystem for Brain V7.

Coordinates four bounded planes:
1. Software plane: capabilities, artifacts and execution health.
2. Cloud plane: workers, jobs, persistence and service health.
3. Knowledge plane: evidence, memories and relationships.
4. Cognitive plane: hypotheses, strategies, simulations and learning.

The ecosystem produces an explainable state and a next-focus recommendation.
It is not a claim of human-level or frontier-model intelligence. It does not
perform external side effects or grant permissions.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Iterable


def clamp(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


@dataclass(frozen=True)
class SoftwareAsset:
    name: str
    health: float = 0.5
    reuse: float = 0.5
    completeness: float = 0.5


@dataclass(frozen=True)
class CloudResource:
    name: str
    availability: float = 0.5
    capacity: float = 0.5
    latency: float = 0.5
    persistent: bool = False


@dataclass(frozen=True)
class KnowledgeEvidence:
    key: str
    reliability: float = 0.5
    freshness: float = 0.5
    corroboration: float = 0.5


@dataclass(frozen=True)
class CognitiveObjective:
    key: str
    value: float
    uncertainty: float
    effort: float
    learning_gain: float


@dataclass(frozen=True)
class EcosystemState:
    software_score: float
    cloud_score: float
    knowledge_score: float
    cognitive_score: float
    integration_score: float


def software_health(assets: Iterable[SoftwareAsset]) -> float:
    rows = list(assets)
    if not rows:
        return 0.0
    return sum(
        clamp(a.health) * 0.45
        + clamp(a.reuse) * 0.20
        + clamp(a.completeness) * 0.35
        for a in rows
    ) / len(rows)


def cloud_health(resources: Iterable[CloudResource]) -> float:
    rows = list(resources)
    if not rows:
        return 0.0
    scores = []
    for r in rows:
        persistence_bonus = 0.10 if r.persistent else 0.0
        scores.append(
            clamp(r.availability) * 0.40
            + clamp(r.capacity) * 0.25
            + clamp(1.0 - r.latency) * 0.20
            + persistence_bonus
        )
    return sum(scores) / len(scores)


def knowledge_quality(evidence: Iterable[KnowledgeEvidence]) -> float:
    rows = list(evidence)
    if not rows:
        return 0.0
    return sum(
        clamp(e.reliability) * 0.45
        + clamp(e.freshness) * 0.25
        + clamp(e.corroboration) * 0.30
        for e in rows
    ) / len(rows)


def cognitive_readiness(objectives: Iterable[CognitiveObjective]) -> float:
    rows = list(objectives)
    if not rows:
        return 0.0
    return sum(
        clamp(o.value) * 0.35
        + (1.0 - clamp(o.uncertainty)) * 0.25
        + (1.0 - clamp(o.effort)) * 0.15
        + clamp(o.learning_gain) * 0.25
        for o in rows
    ) / len(rows)


def integrate(
    assets: Iterable[SoftwareAsset],
    resources: Iterable[CloudResource],
    evidence: Iterable[KnowledgeEvidence],
    objectives: Iterable[CognitiveObjective],
) -> dict:
    s = software_health(assets)
    c = cloud_health(resources)
    k = knowledge_quality(evidence)
    g = cognitive_readiness(objectives)

    # Integration is deliberately bottleneck-sensitive: a weak plane limits
    # the usefulness of the whole ecosystem.
    integration = min(s, c, k, g) * 0.65 + (s + c + k + g) / 4.0 * 0.35
    state = EcosystemState(
        software_score=round(s, 4),
        cloud_score=round(c, 4),
        knowledge_score=round(k, 4),
        cognitive_score=round(g, 4),
        integration_score=round(clamp(integration), 4),
    )

    return {
        "status": "ECOSYSTEM_ASSESSED",
        "planes": {
            "software": round(s, 4),
            "cloud": round(c, 4),
            "knowledge": round(k, 4),
            "cognitive": round(g, 4),
        },
        "state": asdict(state),
        "bottleneck": min(asdict(state), key=asdict(state).get),
        "next_focus": recommend_focus(state),
        "external_side_effects": False,
        "permission_escalation": False,
    }


def recommend_focus(state: EcosystemState) -> str:
    values = asdict(state)
    values.pop("integration_score")
    weakest = min(values, key=values.get)
    mapping = {
        "software_score": "SOFTWARE_ENGINEERING",
        "cloud_score": "CLOUD_RELIABILITY",
        "knowledge_score": "KNOWLEDGE_ACQUISITION",
        "cognitive_score": "COGNITIVE_REASONING",
    }
    return mapping[weakest]


def architecture_layers() -> list[dict]:
    return [
        {"layer": 1, "name": "Execution Fabric", "purpose": "bounded local execution"},
        {"layer": 2, "name": "Cloud Runtime", "purpose": "persistent workers and jobs"},
        {"layer": 3, "name": "Knowledge Graph", "purpose": "evidence and relationships"},
        {"layer": 4, "name": "Long-Term Memory", "purpose": "experience retention"},
        {"layer": 5, "name": "World Model", "purpose": "hypotheses and uncertainty"},
        {"layer": 6, "name": "Cognitive Mesh", "purpose": "parallel specialist reasoning"},
        {"layer": 7, "name": "Meta Learning", "purpose": "learn which strategies work"},
        {"layer": 8, "name": "Adaptive Control", "purpose": "change priorities from feedback"},
        {"layer": 9, "name": "Self Development", "purpose": "select bounded engineering objectives"},
        {"layer": 10, "name": "Economic Intelligence", "purpose": "value and effort analysis"},
        {"layer": 11, "name": "Governance", "purpose": "permissions, audit and safety gates"},
        {"layer": 12, "name": "Verification", "purpose": "provider/evidence confirmation"},
    ]


def ecosystem_snapshot() -> dict:
    return {
        "name": "Brain V7 Cognitive Software-Cloud-Knowledge Ecosystem",
        "planes": ["software", "cloud", "knowledge", "cognitive"],
        "layers": architecture_layers(),
        "closed_loop": [
            "observe",
            "remember",
            "reason",
            "simulate",
            "act_locally",
            "measure",
            "learn",
            "reprioritize",
            "develop",
            "repeat",
        ],
        "autonomy": "bounded",
        "external_side_effects": False,
        "financial_execution": "permission_gated",
        "self_modification": "bounded_and_local",
        "intelligence_claim": "architectural_complexity_only",
    }
