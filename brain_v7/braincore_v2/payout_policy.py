"""Defense-in-depth policy for user-owned payouts."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class PayoutPolicy:
    daily_limit_jod: float = 100.0
    per_transaction_limit_jod: float = 100.0
    require_approval_above_jod: float = 0.0
    allowed_destinations: tuple[str,...] = ()

def authorize(amount_jod:float,destination_ref:str,spent_today_jod:float,
              policy:PayoutPolicy)->dict:
    reasons=[]
    if amount_jod<=0: reasons.append("invalid_amount")
    if amount_jod>policy.per_transaction_limit_jod: reasons.append("transaction_limit")
    if spent_today_jod+amount_jod>policy.daily_limit_jod: reasons.append("daily_limit")
    if policy.allowed_destinations and destination_ref not in policy.allowed_destinations:
        reasons.append("destination_not_allowlisted")
    approval=amount_jod>policy.require_approval_above_jod
    return {"allowed":not reasons,"approval_required":approval or bool(reasons),
            "reasons":reasons,"amount_jod":round(amount_jod,2)}
