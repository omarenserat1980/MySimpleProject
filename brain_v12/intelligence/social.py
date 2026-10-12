"""Social science analysis: demographics, institutions, behavior, inequality, networks."""
from dataclasses import dataclass

@dataclass(frozen=True)
class SocialAnalysis:
    population:str
    institutions:tuple[str,...]
    drivers:tuple[str,...]
    indicators:tuple[str,...]
    evidence_confidence:float

def ready(x:SocialAnalysis)->bool:
    return bool(x.population and x.institutions and x.drivers and x.indicators and 0<=x.evidence_confidence<=1)
