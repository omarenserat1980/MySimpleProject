"""Evidence-gated market/product comparison matrix."""
from __future__ import annotations
from dataclasses import dataclass
from .evidence_engine import Evidence,score

@dataclass(frozen=True)
class MarketCase:
    market:str
    product:str
    price_jod:float|None
    landed_cost_jod:float|None
    evidence:tuple[Evidence,...]=()

def analyze(c:MarketCase)->dict:
    quality=round(sum(score(e) for e in c.evidence)/len(c.evidence),3) if c.evidence else 0.0
    missing=[x for x,v in (("price",c.price_jod),("landed_cost",c.landed_cost_jod)) if v is None]
    if missing:return {"status":"RESEARCH_REQUIRED","market":c.market,"product":c.product,"missing":missing,"evidence_quality":quality}
    return {"status":"EVIDENCE_REVIEW","market":c.market,"product":c.product,
            "gross_profit_jod":round(c.price_jod-c.landed_cost_jod,2),
            "margin":round((c.price_jod-c.landed_cost_jod)/c.price_jod,4) if c.price_jod else 0,
            "evidence_quality":quality}
