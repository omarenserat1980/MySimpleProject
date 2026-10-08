from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

class EvidenceLevel(str, Enum):
    QURAN_TEXT = "L0_QURAN_TEXT"
    HADITH = "L1_HADITH"
    TAFSIR = "L2_TAFSIR"
    LANGUAGE_CONTEXT = "L3_LANGUAGE_CONTEXT"
    HUMAN_KNOWLEDGE = "L4_HUMAN_KNOWLEDGE"
    SCIENTIFIC = "L5_SCIENTIFIC"
    RESEARCH_INFERENCE = "L6_RESEARCH_INFERENCE"
    BRAIN_INFERENCE = "L7_BRAIN_INFERENCE"
    HYPOTHESIS = "L8_HYPOTHESIS"

@dataclass(frozen=True)
class EvidenceRecord:
    id: str
    level: EvidenceLevel
    source: str
    claim: str
    citation: str | None = None
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class QuranicFinding:
    question: str
    finding: str
    evidence: list[EvidenceRecord] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    alternatives: list[str] = field(default_factory=list)
    status: str = "DRAFT"

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "finding": self.finding,
            "evidence": [
                {"id": e.id, "level": e.level.value, "source": e.source,
                 "claim": e.claim, "citation": e.citation,
                 "confidence": e.confidence, "metadata": e.metadata}
                for e in self.evidence
            ],
            "limitations": self.limitations,
            "alternatives": self.alternatives,
            "status": self.status,
        }
