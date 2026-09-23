"""Diversified opportunity allocation without moving money."""
from __future__ import annotations
def allocate(opportunities:list[dict], max_share:float=.35)->list[dict]:
    if not opportunities:return []
    eligible=[x for x in opportunities if x.get("status")=="EVIDENCE_REVIEW" and x.get("gross_profit_jod",0)>0]
    eligible=sorted(eligible,key=lambda x:x.get("evidence_quality",0),reverse=True)
    share=min(max_share,1/len(eligible)) if eligible else 0
    return [{**x,"suggested_attention_share":round(share,3),
             "requires_human_approval":True} for x in eligible]
