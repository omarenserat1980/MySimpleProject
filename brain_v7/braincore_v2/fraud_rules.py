"""Explainable defensive fraud rules."""
from __future__ import annotations
def evaluate(tx:dict)->dict:
    flags=[]
    if tx.get("new_beneficiary") and tx.get("amount_jod",0)>=500: flags.append("new_beneficiary_large_amount")
    if tx.get("velocity_1h",0)>=5: flags.append("high_velocity")
    if tx.get("country_change") and tx.get("amount_jod",0)>=300: flags.append("country_change_large_amount")
    if tx.get("atm_tamper"): flags.append("atm_tamper")
    return {"flags":flags,"risk":"high" if len(flags)>=2 or "atm_tamper" in flags else "medium" if flags else "low"}
