#!/usr/bin/env python3
"""BRAIN V12 Causal Engine.

A dependency-free causal graph engine for modelling cause -> effect relationships,
checking DAG integrity, tracing causal paths, and running simple linear
interventions. It is deliberately conservative: graph structure is evidence of
an assumption, not proof that an edge is causally true.

The design follows standard causal-model practice: explicit graph assumptions,
separation of identification from estimation, and explicit interventions.
See DoWhy's causal graph/model documentation for the corresponding concepts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from collections import defaultdict, deque
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


@dataclass(frozen=True)
class CausalEdge:
    cause: str
    effect: str
    strength: float = 1.0
    evidence: str = "assumption"


@dataclass
class CausalNode:
    name: str
    domain: str = "unknown"
    observed: bool = True
    metadata: Dict[str, str] = field(default_factory=dict)


class CausalEngine:
    """Small, auditable DAG engine used by Brain's decision/orchestration layer."""

    def __init__(self) -> None:
        self.nodes: Dict[str, CausalNode] = {}
        self.edges: List[CausalEdge] = []
        self._children: Dict[str, List[str]] = defaultdict(list)
        self._parents: Dict[str, List[str]] = defaultdict(list)

    def add_node(
        self,
        name: str,
        domain: str = "unknown",
        observed: bool = True,
        metadata: Optional[Mapping[str, str]] = None,
    ) -> None:
        if not name or name.strip() != name:
            raise ValueError("node name must be non-empty and trimmed")
        self.nodes[name] = CausalNode(
            name=name,
            domain=domain,
            observed=observed,
            metadata=dict(metadata or {}),
        )

    def add_edge(
        self,
        cause: str,
        effect: str,
        *,
        strength: float = 1.0,
        evidence: str = "assumption",
    ) -> None:
        if cause not in self.nodes or effect not in self.nodes:
            raise KeyError("both causal edge endpoints must exist")
        if cause == effect:
            raise ValueError("self-causation is not allowed")
        edge = CausalEdge(cause, effect, float(strength), evidence)
        if edge not in self.edges:
            self.edges.append(edge)
            self._children[cause].append(effect)
            self._parents[effect].append(cause)
        if self.has_cycle():
            self.edges.remove(edge)
            self._children[cause].remove(effect)
            self._parents[effect].remove(cause)
            raise ValueError(f"causal cycle rejected: {cause} -> {effect}")

    def has_cycle(self) -> bool:
        indegree = {n: len(self._parents[n]) for n in self.nodes}
        q = deque(n for n, d in indegree.items() if d == 0)
        visited = 0
        while q:
            node = q.popleft()
            visited += 1
            for child in self._children[node]:
                indegree[child] -= 1
                if indegree[child] == 0:
                    q.append(child)
        return visited != len(self.nodes)

    def topological_order(self) -> List[str]:
        if self.has_cycle():
            raise ValueError("causal graph contains a cycle")
        indegree = {n: len(self._parents[n]) for n in self.nodes}
        q = deque(sorted(n for n, d in indegree.items() if d == 0))
        order: List[str] = []
        while q:
            node = q.popleft()
            order.append(node)
            for child in sorted(self._children[node]):
                indegree[child] -= 1
                if indegree[child] == 0:
                    q.append(child)
        return order

    def direct_causes(self, effect: str) -> List[str]:
        self._require_node(effect)
        return sorted(self._parents[effect])

    def direct_effects(self, cause: str) -> List[str]:
        self._require_node(cause)
        return sorted(self._children[cause])

    def causal_paths(self, cause: str, effect: str) -> List[List[str]]:
        self._require_node(cause)
        self._require_node(effect)
        paths: List[List[str]] = []

        def walk(node: str, path: List[str]) -> None:
            if node == effect:
                paths.append(path[:])
                return
            for child in sorted(self._children[node]):
                if child not in path:
                    walk(child, path + [child])

        walk(cause, [cause])
        return paths

    def ancestors(self, node: str) -> List[str]:
        self._require_node(node)
        seen = set()
        stack = list(self._parents[node])
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            stack.extend(self._parents[current])
        return sorted(seen)

    def descendants(self, node: str) -> List[str]:
        self._require_node(node)
        seen = set()
        stack = list(self._children[node])
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            stack.extend(self._children[current])
        return sorted(seen)

    def explain(self, cause: str, effect: str) -> Dict[str, object]:
        paths = self.causal_paths(cause, effect)
        return {
            "cause": cause,
            "effect": effect,
            "causal_path_count": len(paths),
            "paths": paths,
            "direct": effect in self._children[cause],
            "ancestors_of_effect": self.ancestors(effect),
            "assumption_edges": [
                {"cause": e.cause, "effect": e.effect, "evidence": e.evidence}
                for e in self.edges
                if e.evidence == "assumption"
            ],
        }

    def intervene_linear(
        self,
        values: Mapping[str, float],
        intervention: Mapping[str, float],
        coefficients: Mapping[Tuple[str, str], float],
        *,
        baseline: float = 0.0,
    ) -> Dict[str, float]:
        """Propagate a simple linear SCM under do(intervention).

        Each edge (A,B) may have coefficient c, giving:
        B = baseline + sum(c * parent_value).
        Intervention values replace the normal mechanism for those nodes.
        This is a transparent sandbox, not a statistical estimator.
        """
        result = {n: float(values.get(n, baseline)) for n in self.nodes}
        for node, value in intervention.items():
            self._require_node(node)
            result[node] = float(value)

        for node in self.topological_order():
            if node in intervention:
                continue
            parents = self._parents[node]
            if not parents:
                continue
            result[node] = float(baseline) + sum(
                float(coefficients.get((parent, node), 0.0)) * result[parent]
                for parent in parents
            )
        return result

    def to_dict(self) -> Dict[str, object]:
        return {
            "nodes": [
                {
                    "name": n.name,
                    "domain": n.domain,
                    "observed": n.observed,
                    "metadata": n.metadata,
                }
                for n in sorted(self.nodes.values(), key=lambda x: x.name)
            ],
            "edges": [
                {
                    "cause": e.cause,
                    "effect": e.effect,
                    "strength": e.strength,
                    "evidence": e.evidence,
                }
                for e in self.edges
            ],
        }

    def _require_node(self, name: str) -> None:
        if name not in self.nodes:
            raise KeyError(f"unknown causal node: {name}")


def build_cosmic_map() -> CausalEngine:
    """Seed map: broad lawful relationships, not claims of complete causality."""
    g = CausalEngine()
    nodes = [
        ("energy", "physics"),
        ("matter", "physics"),
        ("gravity", "physics"),
        ("motion", "physics"),
        ("temperature", "physics"),
        ("chemical_reactions", "chemistry"),
        ("water", "earth_system"),
        ("atmosphere", "earth_system"),
        ("sunlight", "astronomy"),
        ("photosynthesis", "biology"),
        ("ecosystem", "biology"),
        ("information", "information"),
        ("observation", "epistemology"),
        ("action", "agency"),
        ("outcome", "general"),
    ]
    for name, domain in nodes:
        g.add_node(name, domain=domain)

    edges = [
        ("energy", "temperature", "physical_law"),
        ("gravity", "motion", "physical_law"),
        ("temperature", "chemical_reactions", "physical_law"),
        ("water", "chemical_reactions", "enabling_condition"),
        ("sunlight", "photosynthesis", "biological_mechanism"),
        ("water", "photosynthesis", "biological_condition"),
        ("atmosphere", "ecosystem", "system_condition"),
        ("photosynthesis", "ecosystem", "biological_mechanism"),
        ("information", "observation", "epistemic_dependency"),
        ("observation", "action", "decision_dependency"),
        ("action", "outcome", "intervention"),
    ]
    for cause, effect, evidence in edges:
        g.add_edge(cause, effect, evidence=evidence)
    return g


def self_test() -> None:
    g = build_cosmic_map()
    assert not g.has_cycle()
    assert "energy" in g.ancestors("chemical_reactions")
    assert ["sunlight", "photosynthesis", "ecosystem"] in g.causal_paths(
        "sunlight", "ecosystem"
    )

    # A concrete intervention test: do(energy=5) -> temperature=10 -> reaction=30.
    result = g.intervene_linear(
        values={},
        intervention={"energy": 5.0},
        coefficients={
            ("energy", "temperature"): 2.0,
            ("temperature", "chemical_reactions"): 3.0,
        },
    )
    assert result["temperature"] == 10.0
    assert result["chemical_reactions"] == 30.0

    try:
        g.add_edge("outcome", "action")
    except ValueError:
        pass
    else:
        raise AssertionError("cycle protection failed")


if __name__ == "__main__":
    self_test()
    print("CAUSAL_ENGINE=PASS")


@dataclass
class CausalEvidence:
    cause: str
    effect: str
    observed: int = 0
    successes: int = 0
    failures: int = 0
    source: str = "runtime"

    @property
    def confidence(self) -> float:
        return self.successes / self.observed if self.observed else 0.0


class CausalEvidenceLedger:
    """Append-only-in-memory evidence accumulator for observed outcomes."""

    def __init__(self) -> None:
        self.records: Dict[Tuple[str, str], CausalEvidence] = {}

    def record(
        self,
        cause: str,
        effect: str,
        *,
        success: bool,
        source: str = "runtime",
    ) -> CausalEvidence:
        key = (cause, effect)
        item = self.records.setdefault(
            key, CausalEvidence(cause, effect, source=source)
        )
        item.observed += 1
        if success:
            item.successes += 1
        else:
            item.failures += 1
        return item

    def snapshot(self) -> List[Dict[str, object]]:
        return [
            {
                "cause": r.cause,
                "effect": r.effect,
                "observed": r.observed,
                "successes": r.successes,
                "failures": r.failures,
                "confidence": r.confidence,
                "source": r.source,
            }
            for r in sorted(self.records.values(), key=lambda x: (x.cause, x.effect))
        ]


def causal_audit() -> None:
    """Deterministic audit: graph + evidence ledger must remain internally valid."""
    graph = build_cosmic_map()
    ledger = CausalEvidenceLedger()
    ledger.record("action", "outcome", success=True, source="verification")
    ledger.record("action", "outcome", success=False, source="verification")
    assert not graph.has_cycle()
    assert len(graph.causal_paths("sunlight", "ecosystem")) == 1
    snapshot = ledger.snapshot()
    assert snapshot[0]["observed"] == 2
    assert snapshot[0]["confidence"] == 0.5
