"""Conservative risk decomposition for global trade opportunities."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class RiskInputs:
    supplier:float=0.0
    logistics:float=0.0
    regulatory:float=0.0
    currency:float=0.0
    demand:float=0.0
    evidence_gap:float=0.0

def score(r:RiskInputs)->dict:
    vals={k:max(0.0,min(10.0,v)) for k,v in r.__dict__.items()}
    total=round(sum(vals.values())/len(vals),2)
    return {"components":vals,"overall_risk":total,
            "band":"low" if total<3 else "medium" if total<6 else "high",
            "note":"Risk score is a decision aid, not a forecast."}
