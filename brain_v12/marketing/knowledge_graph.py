"""Evidence-aware marketing knowledge graph."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class KnowledgeNode:
    node_id: str
    kind: str
    title: str
    domain: str

@dataclass(frozen=True)
class KnowledgeEdge:
    source: str
    relation: str
    target: str
    evidence_refs: tuple[str, ...] = ()

class MarketingKnowledgeGraph:
    def __init__(self):
        self.nodes: dict[str, KnowledgeNode] = {}
        self.edges: list[KnowledgeEdge] = []

    def add_node(self, node: KnowledgeNode) -> None:
        if node.node_id in self.nodes:
            raise ValueError("duplicate knowledge node")
        self.nodes[node.node_id]=node

    def link(self, edge: KnowledgeEdge) -> None:
        if edge.source not in self.nodes or edge.target not in self.nodes:
            raise ValueError("knowledge edge references unknown node")
        self.edges.append(edge)

    def neighbors(self, node_id: str) -> tuple[KnowledgeEdge, ...]:
        return tuple(e for e in self.edges if e.source == node_id or e.target == node_id)

    def evidence_backed(self, node_id: str) -> bool:
        return any(node_id in (e.source,e.target) and e.evidence_refs for e in self.edges)
