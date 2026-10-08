"""Defence/security analysis focused on public, strategic and risk-level assessment."""
from dataclasses import dataclass

@dataclass(frozen=True)
class DefenseAnalysis:
    region:str
    period:str
    actors:tuple[str,...]
    strategic_factors:tuple[str,...]
    humanitarian_risks:tuple[str,...]
    evidence_refs:tuple[str,...]

def ready(x:DefenseAnalysis)->bool:
    return bool(x.region and x.period and x.strategic_factors and x.evidence_refs)
