"""China sourcing decision engine: supplier comparison without inventing offers."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class SupplierQuote:
    supplier: str
    unit_price_jod: float
    moq: int
    lead_days: int
    verified: bool = False
    sample_available: bool = False

def rank_suppliers(quotes:list[SupplierQuote]) -> list[dict[str,Any]]:
    rows=[]
    for q in quotes:
        rows.append({
            "supplier":q.supplier,
            "unit_price_jod":q.unit_price_jod,
            "moq":q.moq,
            "lead_days":q.lead_days,
            "verified":q.verified,
            "sample_available":q.sample_available,
            "risk_flags":([] if q.verified else ["supplier_not_verified"]) +
                         ([] if q.sample_available else ["no_sample_evidence"]),
        })
    return sorted(rows,key=lambda x:(not x["verified"],not x["sample_available"],x["unit_price_jod"],x["moq"]))
