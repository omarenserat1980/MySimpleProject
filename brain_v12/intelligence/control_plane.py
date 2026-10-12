"""Cross-domain intelligence control plane."""
from dataclasses import dataclass
from enum import Enum

class Action(str,Enum):
    RESEARCH="RESEARCH"; ANALYZE="ANALYZE"; SCENARIO="SCENARIO"; HOLD="HOLD"

@dataclass(frozen=True)
class DomainSignal:
    domain:str
    confidence:float
    evidence_count:int
    risk:float

@dataclass(frozen=True)
class CrossDomainResult:
    action:Action
    confidence:float
    domains:tuple[str,...]
    rationale:str

def synthesize(signals:tuple[DomainSignal,...])->CrossDomainResult:
    if not signals:
        return CrossDomainResult(Action.RESEARCH,0.0,(),"no domain evidence")
    if any(not 0<=s.confidence<=1 or s.evidence_count<0 or not 0<=s.risk<=1 for s in signals):
        raise ValueError("invalid domain signal")
    conf=sum(s.confidence for s in signals)/len(signals)
    domains=tuple(s.domain for s in signals)
    if any(s.risk>.7 for s in signals): return CrossDomainResult(Action.HOLD,conf,domains,"material risk requires review")
    if any(s.evidence_count==0 for s in signals): return CrossDomainResult(Action.RESEARCH,conf,domains,"missing evidence")
    if conf<.7: return CrossDomainResult(Action.ANALYZE,conf,domains,"evidence is not yet strong enough for scenario commitment")
    return CrossDomainResult(Action.SCENARIO,conf,domains,"cross-domain evidence supports scenario analysis")
