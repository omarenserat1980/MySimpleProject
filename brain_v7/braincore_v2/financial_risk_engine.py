"""Financial transaction risk scoring; decision aid, not a fraud verdict."""
from __future__ import annotations
def score(*,amount_jod:float,velocity:float,device_change:float,geo_anomaly:float,
         beneficiary_new:float,chargeback_history:float)->dict:
    vals={k:max(0,min(10,float(v))) for k,v in {
        "amount":min(10,amount_jod/1000),"velocity":velocity,"device_change":device_change,
        "geo_anomaly":geo_anomaly,"beneficiary_new":beneficiary_new,
        "chargeback_history":chargeback_history}.items()}
    total=round(sum(vals.values())/len(vals),2)
    return {"risk_score":total,"band":"low" if total<3 else "medium" if total<6 else "high",
            "components":vals,"requires_review":total>=6}
