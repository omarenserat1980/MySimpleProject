"""Jordan import landed-cost calculator.

This module is a calculation engine, not a customs ruling. Rates must be
provided from current official sources for the specific HS code/product.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any

@dataclass(frozen=True)
class ImportQuote:
    product_value_jod: float
    inland_origin_jod: float = 0.0
    international_freight_jod: float = 0.0
    insurance_jod: float = 0.0
    customs_rate: float = 0.0
    sales_tax_rate: float = 0.0
    other_duties_jod: float = 0.0
    clearance_jod: float = 0.0
    destination_transport_jod: float = 0.0

def calculate(q: ImportQuote) -> dict[str, Any]:
    customs_base=max(0.0,q.product_value_jod+q.inland_origin_jod+
                     q.international_freight_jod+q.insurance_jod)
    customs=max(0.0,customs_base*q.customs_rate)
    tax_base=customs_base+customs+q.other_duties_jod
    sales_tax=max(0.0,tax_base*q.sales_tax_rate)
    landed=customs_base+customs+q.other_duties_jod+sales_tax+q.clearance_jod+q.destination_transport_jod
    return {
        "bases": {"customs_base":round(customs_base,2),"tax_base":round(tax_base,2)},
        "charges": {"customs":round(customs,2),"sales_tax":round(sales_tax,2),
                    "other_duties":round(q.other_duties_jod,2),
                    "clearance":round(q.clearance_jod,2),
                    "destination_transport":round(q.destination_transport_jod,2)},
        "landed_cost_jod":round(landed,2),
        "source_rates_required": True,
        "warning":"Rates and tax bases must be verified for the exact HS code and shipment regime before purchase."
    }
