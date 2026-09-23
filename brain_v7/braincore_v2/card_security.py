"""Defensive card/ATM security telemetry model."""
from __future__ import annotations
def assess(*,pin_failures:int,atm_tamper_alert:bool,offline_anomaly:bool,
           unusual_withdrawal:bool)->dict:
    flags=[]
    if pin_failures>=3: flags.append("repeated_pin_failures")
    if atm_tamper_alert: flags.append("atm_tamper_alert")
    if offline_anomaly: flags.append("offline_transaction_anomaly")
    if unusual_withdrawal: flags.append("unusual_withdrawal")
    return {"flags":flags,"severity":"critical" if "atm_tamper_alert" in flags
            else "high" if len(flags)>=2 else "medium" if flags else "normal",
            "action":"BLOCK_AND_INVESTIGATE" if "atm_tamper_alert" in flags else
                     "REVIEW" if flags else "MONITOR"}
