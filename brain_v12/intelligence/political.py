"""Neutral political analysis: institutions, policy, actors and documented positions."""
from dataclasses import dataclass

@dataclass(frozen=True)
class PoliticalAnalysis:
    jurisdiction:str
    period:str
    institutions:tuple[str,...]
    policy_issues:tuple[str,...]
    documented_positions:tuple[str,...]
    evidence_refs:tuple[str,...]

def ready(x:PoliticalAnalysis)->bool:
    return bool(x.jurisdiction and x.period and x.policy_issues and x.evidence_refs)
