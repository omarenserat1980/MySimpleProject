from dataclasses import dataclass
from enum import Enum

class IntelligenceDomain(str,Enum):
    SOCIAL="SOCIAL"; POLITICAL="POLITICAL"; ECONOMIC="ECONOMIC"; DEFENSE="DEFENSE"

@dataclass(frozen=True)
class IntelligenceAssessment:
    domain:IntelligenceDomain
    question:str
    facts:tuple[str,...]
    assumptions:tuple[str,...]
    scenarios:tuple[str,...]
    confidence:float
    sources:tuple[str,...]

def validate(a:IntelligenceAssessment)->bool:
    if not a.question or not 0<=a.confidence<=1: raise ValueError("invalid assessment")
    return bool(a.facts or a.sources)
