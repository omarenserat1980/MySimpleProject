from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable
from .integrity import QuranIntegrityGate
from .models import EvidenceLevel, EvidenceRecord, QuranicFinding

@dataclass
class QuranicResearchEngine:
    gate: QuranIntegrityGate

    def __init__(self, gate: QuranIntegrityGate | None = None):
        self.gate = gate or QuranIntegrityGate()

    def evidence_id(self, level: EvidenceLevel, source: str, claim: str) -> str:
        return sha256(f"{level.value}|{source}|{claim}".encode()).hexdigest()[:16]

    def make_evidence(self, level, source, claim, citation=None, confidence=0.0, metadata=None):
        return EvidenceRecord(
            id=self.evidence_id(level, source, claim), level=level, source=source,
            claim=claim, citation=citation, confidence=confidence, metadata=metadata or {}
        )

    def research(self, question: str, evidence: Iterable[EvidenceRecord], finding: str,
                 limitations=(), alternatives=()) -> QuranicFinding:
        records = list(evidence)
        result = self.gate.validate(records)
        if not result.allowed:
            raise ValueError("QURAN_INTEGRITY_GATE_BLOCKED: " + "; ".join(result.reasons))
        return QuranicFinding(
            question=question.strip(), finding=finding.strip(), evidence=records,
            limitations=list(limitations), alternatives=list(alternatives),
            status="VERIFIED_STRUCTURE" if self.gate.publication_allowed(records) else "BLOCKED",
        )

    def pipeline(self, question: str) -> dict:
        return {
            "question": question.strip(),
            "stages": [
                "SOURCE_LOCK", "LANGUAGE_AND_CONTEXT", "TAFSIR_COMPARISON",
                "HUMAN_KNOWLEDGE", "SCIENTIFIC_CHECK", "COUNTER_EVIDENCE",
                "INTEGRITY_GATE", "HUMAN_BENEFIT", "PUBLISH_OR_HOLD"
            ],
            "rules": [
                "Never modify canonical Quran text.",
                "Never present Brain inference as Quranic text.",
                "Separate tafsir, scientific evidence, inference, and hypothesis.",
                "Search for counter-evidence before publication.",
                "If evidence is insufficient, return HOLD rather than fabricate.",
            ],
        }
