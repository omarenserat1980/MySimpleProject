"""Detect payout inconsistencies; never silently mark money as received."""
from __future__ import annotations
def check(expected_amount_jod:float,ledger_status:str,provider_amount_jod:float|None,
          provider_reference:str|None)->dict:
    issues=[]
    if ledger_status=="CONFIRMED" and not provider_reference:
        issues.append("missing_provider_reference")
    if provider_amount_jod is not None and abs(provider_amount_jod-expected_amount_jod)>.01:
        issues.append("amount_mismatch")
    if ledger_status=="CONFIRMED" and provider_amount_jod is None:
        issues.append("provider_amount_missing")
    return {"reconciled":not issues,"issues":issues}
