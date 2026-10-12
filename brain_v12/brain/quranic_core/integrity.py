from __future__ import annotations
from dataclasses import dataclass
from .models import EvidenceLevel, EvidenceRecord

@dataclass(frozen=True)
class IntegrityResult:
    allowed: bool
    reasons: tuple[str, ...]

class QuranIntegrityGate:
    FORBIDDEN_AS_QURAN = (
        "بحسب برين",
        "استنتج برين",
        "الله يقصد قطعًا",
        "هذا اكتشاف علمي قرآني",
    )

    def validate(self, records: list[EvidenceRecord]) -> IntegrityResult:
        reasons: list[str] = []
        for record in records:
            if not record.claim.strip():
                reasons.append(f"{record.id}: empty claim")
            if record.level == EvidenceLevel.QURAN_TEXT and not record.citation:
                reasons.append(f"{record.id}: Quran text requires a citation")
            if not 0 <= record.confidence <= 1:
                reasons.append(f"{record.id}: confidence must be between 0 and 1")
            if any(x.lower() in record.claim.lower() for x in self.FORBIDDEN_AS_QURAN):
                reasons.append(f"{record.id}: unsafe attribution")
        return IntegrityResult(not reasons, tuple(reasons))

    @staticmethod
    def publication_allowed(records: list[EvidenceRecord]) -> bool:
        result = QuranIntegrityGate().validate(records)
        if not result.allowed:
            return False
        return not any(
            r.level == EvidenceLevel.BRAIN_INFERENCE and r.metadata.get("present_as") == "quran"
            for r in records
        )
