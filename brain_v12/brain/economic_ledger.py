"""Evidence-based economic ledger for Brain.

Expected, claimed and earned amounts are never treated as received revenue.
A balance becomes verified only after an externally supplied payment receipt is
validated by the selected payment adapter. This module itself never moves money.
"""
from __future__ import annotations
import json, time
from pathlib import Path

STATES={"EXPECTED","CLAIMED","EARNED","VERIFIED_RECEIVED","REJECTED"}

class EconomicLedger:
    def __init__(self, path="brain6_artifacts/economy/ledger.jsonl"):
        self.path=Path(path)
        self.path.parent.mkdir(parents=True,exist_ok=True)

    def record(self, opportunity_id, state, amount, currency="JOD", evidence=None, source=None):
        state=str(state).upper()
        if state not in STATES:
            raise ValueError("invalid_economic_state")
        row={
            "ts":time.time(),"opportunity_id":opportunity_id,"state":state,
            "amount":float(amount),"currency":currency,
            "evidence":evidence or {},"source":source or {}
        }
        with self.path.open("a",encoding="utf-8") as f:
            f.write(json.dumps(row,ensure_ascii=False)+"\n")
        return row

    def verified_total(self, currency="JOD"):
        total=0.0
        if not self.path.exists():
            return total
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row=json.loads(line)
            if row.get("state")=="VERIFIED_RECEIVED" and row.get("currency")==currency:
                total += float(row.get("amount",0))
        return round(total, 8)

    def snapshot(self):
        return {
            "verified_revenue": {
                "JOD": self.verified_total("JOD"),
                "USD": self.verified_total("USD"),
                "USDC": self.verified_total("USDC"),
            },
            "policy":{
                "advertised_amount_is_not_revenue":True,
                "verified_payment_evidence_required":True,
                "money_movement": "policy_gated",
                "withdrawal": "policy_gated",
            }
        }

if __name__ == "__main__":
    print(json.dumps(EconomicLedger().snapshot(), indent=2))
