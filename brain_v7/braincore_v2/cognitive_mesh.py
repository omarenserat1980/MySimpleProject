"""Cognitive Mesh for Brain V7.

A bounded internal mesh of specialized reasoning roles. Each node produces an
independent assessment; a synthesizer reconciles disagreement, uncertainty,
causal evidence, and resource cost into one explainable cognitive state.

This is software architecture, not a claim that the system exceeds a
frontier language model. It performs no external side effects and grants no
new permissions.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Iterable


def clamp(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


@dataclass(frozen=True)
class CognitiveNode:
    node_id: str
    role: str
    focus: str
    reliability: float = 0.5
    cost: float = 0.2


@dataclass(frozen=True)
class NodeAssessment:
    node_id: str
    hypothesis: str
    confidence: float
    evidence: float
    risk: float
    value: float
    rationale: str = ""


@dataclass(frozen=True)
class Conflict:
    hypothesis_a: str
    hypothesis_b: str
    disagreement: float
    resolution_need: str


DEFAULT_NODES = (
    CognitiveNode("observer", "OBSERVE", "signals and anomalies", 0.70, 0.10),
    CognitiveNode("analyst", "ANALYZE", "patterns and evidence", 0.72, 0.20),
    CognitiveNode("causal", "CAUSAL", "causes and consequences", 0.65, 0.25),
    CognitiveNode("strategist", "STRATEGY", "alternative strategies", 0.65, 0.25),
    CognitiveNode("simulator", "SIMULATE", "counterfactual outcomes", 0.60, 0.35),
    CognitiveNode("economist", "ECONOMICS", "value, effort and opportunity cost", 0.68, 0.20),
    CognitiveNode("risk", "RISK", "failure and downside", 0.75, 0.15),
    CognitiveNode("learner", "LEARN", "information gain and reusable knowledge", 0.60, 0.20),
)


def assess(
    node: CognitiveNode,
    hypothesis: str,
    *,
    evidence: float,
    confidence: float,
    risk: float,
    value: float,
    rationale: str = "",
) -> NodeAssessment:
    return NodeAssessment(
        node_id=node.node_id,
        hypothesis=hypothesis,
        confidence=clamp(confidence * node.reliability),
        evidence=clamp(evidence),
        risk=clamp(risk),
        value=clamp(value),
        rationale=rationale,
    )


def detect_conflicts(assessments: Iterable[NodeAssessment]) -> list[Conflict]:
    rows = list(assessments)
    conflicts: list[Conflict] = []
    for i, left in enumerate(rows):
        for right in rows[i + 1:]:
            if left.hypothesis == right.hypothesis:
                continue
            disagreement = clamp(
                abs(left.value - right.value) * 0.45
                + abs(left.confidence - right.confidence) * 0.30
                + abs(left.risk - right.risk) * 0.25
            )
            if disagreement >= 0.30:
                conflicts.append(Conflict(
                    left.hypothesis,
                    right.hypothesis,
                    round(disagreement, 4),
                    "REQUIRE_EVIDENCE_OR_SIMULATION",
                ))
    return sorted(conflicts, key=lambda x: x.disagreement, reverse=True)


def synthesize(assessments: Iterable[NodeAssessment]) -> dict:
    rows = list(assessments)
    if not rows:
        return {"status": "NO_ASSESSMENTS"}

    by_hypothesis: dict[str, list[NodeAssessment]] = {}
    for row in rows:
        by_hypothesis.setdefault(row.hypothesis, []).append(row)

    candidates = []
    for hypothesis, group in by_hypothesis.items():
        total_weight = sum(max(0.05, x.confidence) for x in group)
        value = sum(x.value * max(0.05, x.confidence) for x in group) / total_weight
        evidence = sum(x.evidence * max(0.05, x.confidence) for x in group) / total_weight
        risk = sum(x.risk * max(0.05, x.confidence) for x in group) / total_weight
        confidence = clamp(
            sum(x.confidence for x in group) / len(group)
            * (0.70 + 0.30 * evidence)
        )
        score = clamp(
            value * 0.40
            + confidence * 0.30
            + evidence * 0.20
            + (1.0 - risk) * 0.10
        )
        candidates.append({
            "hypothesis": hypothesis,
            "score": round(score, 4),
            "value": round(value, 4),
            "evidence": round(evidence, 4),
            "risk": round(risk, 4),
            "confidence": round(confidence, 4),
            "node_count": len(group),
        })

    candidates.sort(key=lambda x: x["score"], reverse=True)
    conflicts = detect_conflicts(rows)
    return {
        "status": "SYNTHESIZED",
        "candidates": candidates,
        "conflicts": [asdict(c) for c in conflicts[:20]],
        "conflict_count": len(conflicts),
        "needs_more_evidence": bool(conflicts and conflicts[0].disagreement >= 0.55),
        "external_side_effects": False,
        "permission_escalation": False,
    }


def run_mesh(
    hypothesis: str,
    *,
    evidence: float = 0.5,
    confidence: float = 0.5,
    risk: float = 0.5,
    value: float = 0.5,
    nodes: Iterable[CognitiveNode] = DEFAULT_NODES,
) -> dict:
    """Run parallel specialist assessments and synthesize them."""
    assessments = []
    for node in nodes:
        role_adjustment = {
            "RISK": -0.10,
            "ECONOMICS": 0.05,
            "OBSERVE": 0.02,
            "LEARN": 0.00,
        }.get(node.role, 0.0)
        assessments.append(assess(
            node,
            hypothesis,
            evidence=evidence,
            confidence=clamp(confidence + role_adjustment),
            risk=risk,
            value=value,
            rationale=f"{node.role} specialist assessment",
        ))

    synthesis = synthesize(assessments)
    return {
        "architecture": "cognitive_mesh_v1",
        "parallel_nodes": len(assessments),
        "assessments": [asdict(x) for x in assessments],
        "synthesis": synthesis,
        "next_action": (
            "GATHER_MORE_EVIDENCE"
            if synthesis.get("needs_more_evidence")
            else "FEED_TO_META_LEARNING"
        ),
        "simulation_only": True,
    }


def mesh_snapshot() -> dict:
    return {
        "nodes": [asdict(x) for x in DEFAULT_NODES],
        "reasoning_pattern": [
            "parallel_specialists",
            "conflict_detection",
            "evidence_weighting",
            "synthesis",
            "meta_learning_feedback",
        ],
        "bounded": True,
        "external_side_effects": False,
        "permission_escalation": False,
    }
