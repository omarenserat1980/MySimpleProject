#!/usr/bin/env python3
"""Verse-by-verse Quran knowledge pipeline for BRAIN.

This layer creates a reviewable record for every ayah. It separates:
1) the Quran text,
2) attributed tafsir,
3) linguistic/topic analysis,
4) engineering hypotheses.

No automatic model output is treated as tafsir or revelation.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, List


@dataclass(frozen=True)
class AyahKnowledgeRecord:
    verse_key: str
    text_sha256: str
    text_status: str = "SOURCE_REGISTERED"
    tafsir_status: str = "REQUIRES_ATTRIBUTED_SOURCE"
    topic_status: str = "REQUIRES_REVIEW"
    causal_status: str = "REQUIRES_EVIDENCE"
    engineering_status: str = "HYPOTHESIS_ONLY"

    def validate(self) -> None:
        if not self.verse_key or ":" not in self.verse_key:
            raise ValueError("invalid verse key")
        if len(self.text_sha256) != 64:
            raise ValueError("invalid text hash")
        allowed = {
            "SOURCE_REGISTERED",
            "SOURCE_VERIFIED",
        }
        if self.text_status not in allowed:
            raise ValueError("invalid text status")
        if self.engineering_status != "HYPOTHESIS_ONLY":
            raise ValueError(
                "engineering claims require explicit evidence and review"
            )


class AyahKnowledgePipeline:
    """Deterministic boundary between scripture and downstream analysis."""

    def register(self, verse_key: str, text_sha256: str) -> Dict[str, object]:
        record = AyahKnowledgeRecord(verse_key, text_sha256)
        record.validate()
        return asdict(record)

    def promote_tafsir(
        self, record: Dict[str, object], source: str, citation: str
    ) -> Dict[str, object]:
        if not source.strip() or not citation.strip():
            raise ValueError("tafsir source and citation are required")
        updated = dict(record)
        updated["tafsir_status"] = "ATTRIBUTED_SOURCE"
        updated["tafsir_source"] = source
        updated["tafsir_citation"] = citation
        return updated

    def promote_evidence(
        self, record: Dict[str, object], evidence: List[str]
    ) -> Dict[str, object]:
        if not evidence:
            raise ValueError("evidence is required")
        updated = dict(record)
        updated["causal_status"] = "EVIDENCE_RECORDED"
        updated["evidence"] = list(evidence)
        return updated


def self_test() -> None:
    p = AyahKnowledgePipeline()
    r = p.register("1:1", "0" * 64)
    assert r["tafsir_status"] == "REQUIRES_ATTRIBUTED_SOURCE"
    assert r["engineering_status"] == "HYPOTHESIS_ONLY"
    r = p.promote_tafsir(r, "named source", "1:1 discussion")
    assert r["tafsir_status"] == "ATTRIBUTED_SOURCE"
    r = p.promote_evidence(r, ["documented observation"])
    assert r["causal_status"] == "EVIDENCE_RECORDED"


if __name__ == "__main__":
    self_test()
    print("QURAN_AYAH_KNOWLEDGE_PIPELINE=PASS")
