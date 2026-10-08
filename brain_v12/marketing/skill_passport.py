"""Evidence-backed marketing skill passport."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class SkillEvidence:
    skill: str
    source: str
    score: float
    real_world: bool = False

@dataclass(frozen=True)
class SkillStatus:
    skill: str
    level: str
    score: float
    evidence_count: int
    real_world_evidence: int

def assess_skill(skill: str, evidence: tuple[SkillEvidence,...]) -> SkillStatus:
    if not skill:
        raise ValueError("skill is required")
    relevant=[x for x in evidence if x.skill==skill]
    if any(not 0 <= x.score <= 1 for x in relevant):
        raise ValueError("score must be between 0 and 1")
    if not relevant:
        return SkillStatus(skill,"UNASSESSED",0.0,0,0)
    score=max(x.score for x in relevant)
    real=sum(x.real_world for x in relevant)
    if score < .55: level="FOUNDATION"
    elif score < .75: level="PRACTITIONER"
    elif score < .90: level="ADVANCED"
    elif real >= 2: level="EXPERT"
    else: level="ADVANCED"
    return SkillStatus(skill,level,score,len(relevant),real)

def expert_claim_allowed(status: SkillStatus) -> bool:
    return status.level=="EXPERT" and status.real_world_evidence>=2
