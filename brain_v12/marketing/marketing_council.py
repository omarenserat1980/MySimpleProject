"""Marketing Council: deterministic specialist synthesis."""
from __future__ import annotations
from dataclasses import dataclass
from .marketing_domains import MarketingDomain, curriculum
from .marketing_expert import MarketingDecision, MarketingEvidence, decide

@dataclass(frozen=True)
class SpecialistOpinion:
    domain: str
    question: str
    recommendation: str
    evidence_count: int

@dataclass(frozen=True)
class CouncilResult:
    question: str
    specialists: tuple[SpecialistOpinion, ...]
    decision: MarketingDecision

def convene(question: str, *, evidence: tuple[MarketingEvidence, ...] = ()) -> CouncilResult:
    if not question.strip():
        raise ValueError("question is required")
    opinions=[]
    for domain in curriculum():
        opinions.append(SpecialistOpinion(
            domain=domain.id,
            question=question,
            recommendation=f"Evaluate through {domain.name}.",
            evidence_count=len(evidence),
        ))
    decision=decide(
        hypothesis=question,
        success_metric="validated_business_outcome",
        evidence=evidence,
    )
    return CouncilResult(question, tuple(opinions), decision)
