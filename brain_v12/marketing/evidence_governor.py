"""Governance for marketing knowledge and decisions."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

class EvidenceGrade(str, Enum):
    UNVERIFIED="UNVERIFIED"
    WEAK="WEAK"
    MODERATE="MODERATE"
    STRONG="STRONG"

@dataclass(frozen=True)
class EvidenceItem:
    ref: str
    source_type: str
    confidence: float
    independent_sources: int = 1
    real_world_result: bool = False

def grade(e: EvidenceItem) -> EvidenceGrade:
    if not e.ref or not 0 <= e.confidence <= 1:
        raise ValueError("invalid evidence")
    if e.real_world_result and e.confidence >= .85 and e.independent_sources >= 2:
        return EvidenceGrade.STRONG
    if e.confidence >= .70 or e.independent_sources >= 2:
        return EvidenceGrade.MODERATE
    if e.confidence >= .40:
        return EvidenceGrade.WEAK
    return EvidenceGrade.UNVERIFIED

def allow_for_action(items: tuple[EvidenceItem, ...], *, high_impact: bool=False) -> bool:
    if not items:
        return False
    grades=[grade(x) for x in items]
    if high_impact:
        return EvidenceGrade.STRONG in grades
    return any(x in {EvidenceGrade.MODERATE,EvidenceGrade.STRONG} for x in grades)
