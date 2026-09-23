"""Double-entry-inspired transaction reconciliation."""
from __future__ import annotations
def reconcile(expected:dict,actual:dict)->dict:
    fields=("amount_jod","currency","provider_reference")
    mismatches=[f for f in fields if expected.get(f)!=actual.get(f)]
    return {"matched":not mismatches,"mismatches":mismatches}
