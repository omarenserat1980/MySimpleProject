from __future__ import annotations
from dataclasses import dataclass
from .models import EvidenceRecord, EvidenceLevel

@dataclass
class CounterEvidenceEngine:
    def evaluate(self, claim: str, evidence: list[EvidenceRecord]) -> dict:
        opposing = [
            e for e in evidence
            if e.metadata.get("relation") in {"counter", "opposing", "contradictory"}
        ]
        return {
            "claim": claim,
            "counter_evidence_count": len(opposing),
            "counter_evidence": [
                {"id": e.id, "source": e.source, "claim": e.claim,
                 "level": e.level.value, "confidence": e.confidence}
                for e in opposing
            ],
            "status": "COUNTER_EVIDENCE_FOUND" if opposing else "NO_COUNTER_EVIDENCE_RECORDED",
            "warning": "Absence of recorded counter-evidence is not proof of truth."
                if not opposing else None,
        }
