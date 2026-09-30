#!/usr/bin/env python3
"""Deterministic Quran Knowledge Graph layer for BRAIN.

The graph stores relationships between ayahs and explicitly attributed
annotations. It does not invent tafsir, doctrine, or scientific conclusions.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, List


@dataclass(frozen=True)
class KnowledgeEdge:
    source: str
    relation: str
    target: str
    evidence: str
    confidence: str = "UNASSESSED"


class QuranKnowledgeGraph:
    def __init__(self) -> None:
        self.nodes: Dict[str, Dict[str, object]] = {}
        self.edges: List[KnowledgeEdge] = []

    def add_ayah(self, verse_key: str, text_sha256: str) -> None:
        self.nodes[verse_key] = {
            "type": "ayah",
            "text_sha256": text_sha256,
            "semantic_status": "UNASSESSED",
        }

    def add_concept(self, concept_id: str, label: str, source: str) -> None:
        self.nodes[concept_id] = {
            "type": "concept",
            "label": label,
            "source": source,
        }

    def link(
        self,
        source: str,
        relation: str,
        target: str,
        evidence: str,
        confidence: str = "UNASSESSED",
    ) -> None:
        if source not in self.nodes or target not in self.nodes:
            raise KeyError("both graph nodes must exist")
        if not evidence.strip():
            raise ValueError("evidence/citation is required")
        self.edges.append(
            KnowledgeEdge(source, relation, target, evidence, confidence)
        )

    def neighbors(self, node: str) -> List[Dict[str, object]]:
        return [
            asdict(e)
            for e in self.edges
            if e.source == node or e.target == node
        ]

    def audit(self) -> Dict[str, int]:
        return {
            "nodes": len(self.nodes),
            "edges": len(self.edges),
            "uncited_edges": sum(not e.evidence.strip() for e in self.edges),
        }

    def export(self) -> Dict[str, object]:
        return {
            "nodes": self.nodes,
            "edges": [asdict(e) for e in self.edges],
            "policy": {
                "automatic_tafsir": False,
                "scientific_claims_without_external_evidence": False,
                "citation_required_for_semantic_edges": True,
            },
        }


def self_test() -> None:
    g = QuranKnowledgeGraph()
    g.add_ayah("1:1", "0" * 64)
    g.add_concept("mercy", "الرحمة", "REVIEW_REQUIRED")
    g.link("1:1", "MENTIONS_OR_RELATES_TO", "mercy", "1:1; attributed linguistic review")
    assert g.audit()["nodes"] == 2
    assert g.audit()["uncited_edges"] == 0
    assert len(g.neighbors("1:1")) == 1


if __name__ == "__main__":
    self_test()
    print("QURAN_KNOWLEDGE_GRAPH=PASS")
