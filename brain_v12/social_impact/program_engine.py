"""Program design and theory-of-change primitives."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Program:
    program_id:str
    problem:str
    beneficiaries:str
    activities:tuple[str,...]
    outputs:tuple[str,...]
    outcomes:tuple[str,...]
    impact:str
    evidence_confidence:float

def readiness(p:Program)->float:
    if not p.problem or not p.beneficiaries or not p.activities or not p.outputs or not p.outcomes or not p.impact:
        return 0.0
    if not 0<=p.evidence_confidence<=1: raise ValueError("confidence must be 0..1")
    return .15*bool(p.problem)+.15*bool(p.beneficiaries)+.15*bool(p.activities)+.15*bool(p.outputs)+.20*bool(p.outcomes)+.10*bool(p.impact)+.10*p.evidence_confidence
