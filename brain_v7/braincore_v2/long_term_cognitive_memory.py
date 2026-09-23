"""Long-term cognitive memory and iterative inference for Brain V7.

Stores bounded, structured memories and derives new hypotheses through repeated
local inference. Memory is evidence-weighted; weak observations decay in
confidence. This module does not grant permissions or perform external actions.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from time import time
from typing import Iterable


def clamp(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


@dataclass
class MemoryNode:
    key: str
    concept: str
    belief: float = 0.5
    confidence: float = 0.2
    observations: int = 0
    successes: int = 0
    failures: int = 0
    last_updated: float = 0.0

    @property
    def stability(self) -> float:
        return clamp(self.confidence * min(1.0, self.observations / 10.0))


@dataclass(frozen=True)
class MemoryObservation:
    key: str
    outcome: float
    reliability: float = 0.5
    source: str = "local"
    timestamp: float = 0.0


@dataclass(frozen=True)
class Relation:
    source: str
    target: str
    relation: str
    strength: float = 0.5


def absorb(node: MemoryNode, observation: MemoryObservation) -> MemoryNode:
    reliability = clamp(observation.reliability)
    outcome = clamp(observation.outcome)
    node.observations += 1
    node.successes += int(outcome >= 0.5)
    node.failures += int(outcome < 0.5)

    # Diminishing update rate prevents a single event from dominating memory.
    alpha = max(0.05, min(0.35, reliability / (node.observations + 1)))
    node.belief = clamp(node.belief + alpha * (outcome - node.belief))
    node.confidence = clamp(
        node.confidence + alpha * (reliability - node.confidence)
        + 0.03 * min(1.0, node.observations / 10.0)
    )
    node.last_updated = observation.timestamp or time()
    return node


def consolidate(
    nodes: Iterable[MemoryNode],
    observations: Iterable[MemoryObservation],
) -> dict[str, MemoryNode]:
    memory = {n.key: n for n in nodes}
    for obs in observations:
        memory.setdefault(obs.key, MemoryNode(
            key=obs.key,
            concept=obs.key,
            last_updated=obs.timestamp or time(),
        ))
        absorb(memory[obs.key], obs)
    return memory


def propagate(
    memory: dict[str, MemoryNode],
    relations: Iterable[Relation],
) -> list[dict]:
    """Propagate only a bounded fraction of belief across known relations."""
    derived = []
    for relation in relations:
        src = memory.get(relation.source)
        dst = memory.get(relation.target)
        if not src or not dst:
            continue
        strength = clamp(relation.strength)
        influence = (src.belief - 0.5) * strength * src.confidence * 0.25
        predicted = clamp(dst.belief + influence)
        derived.append({
            "source": relation.source,
            "target": relation.target,
            "relation": relation.relation,
            "predicted_belief": round(predicted, 4),
            "influence": round(influence, 4),
        })
    return derived


def infer(
    memory: dict[str, MemoryNode],
    relations: Iterable[Relation],
    *,
    iterations: int = 3,
) -> dict:
    """Run bounded recurrent inference without uncontrolled recursion."""
    iterations = max(1, min(10, int(iterations)))
    state = {k: MemoryNode(**asdict(v)) for k, v in memory.items()}
    history = []

    for step in range(iterations):
        predictions = propagate(state, relations)
        for p in predictions:
            target = state[p["target"]]
            target.belief = clamp(
                target.belief + p["influence"] * 0.5
            )
        history.append({
            "iteration": step + 1,
            "predictions": predictions,
        })

    ranked = sorted(
        (
            {
                "key": n.key,
                "belief": round(n.belief, 4),
                "confidence": round(n.confidence, 4),
                "stability": round(n.stability, 4),
                "observations": n.observations,
            }
            for n in state.values()
        ),
        key=lambda x: x["confidence"] * x["belief"],
        reverse=True,
    )
    return {
        "status": "INFERENCE_COMPLETE",
        "iterations": iterations,
        "memory_size": len(state),
        "ranked_beliefs": ranked,
        "history": history,
        "external_side_effects": False,
        "permission_escalation": False,
    }


def recall(memory: dict[str, MemoryNode], key: str) -> dict | None:
    node = memory.get(key)
    return asdict(node) if node else None


def memory_snapshot(memory: dict[str, MemoryNode]) -> dict:
    return {
        "nodes": [asdict(n) for n in memory.values()],
        "count": len(memory),
        "stable_nodes": sum(n.stability >= 0.6 for n in memory.values()),
        "learning_enabled": True,
        "external_side_effects": False,
    }
