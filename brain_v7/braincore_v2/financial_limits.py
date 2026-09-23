"""Conservative financial controls."""
from __future__ import annotations
def check(amount_jod:float,daily_total_jod:float,daily_limit_jod:float,
          account_balance_jod:float,reserve_jod:float)->dict:
    reasons=[]
    if amount_jod<=0: reasons.append("invalid_amount")
    if daily_total_jod+amount_jod>daily_limit_jod: reasons.append("daily_limit")
    if account_balance_jod-amount_jod<reserve_jod: reasons.append("reserve_breach")
    return {"allowed":not reasons,"reasons":reasons}
