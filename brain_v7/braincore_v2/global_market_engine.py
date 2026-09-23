"""Global market intelligence layer.

A neutral framework for comparing markets without inventing live prices,
demand, tariffs, or regulations. External evidence must be supplied before
a market is treated as verified.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any

@dataclass(frozen=True)
class MarketSnapshot:
    market: str
    country: str
    currency: str
    product: str
    observed_price: float | None = None
    demand_score: float | None = None
    competition_score: float | None = None
    shipping_cost: float | None = None
    tariff_rate: float | None = None
    source_url: str | None = None
    verified_at: str | None = None

def completeness(s: MarketSnapshot) -> float:
    fields=("observed_price","demand_score","competition_score","shipping_cost","tariff_rate","source_url","verified_at")
    return round(sum(getattr(s,f) is not None for f in fields)/len(fields),2)

def compare_markets(snapshots:list[MarketSnapshot]) -> list[dict[str,Any]]:
    """Return comparable evidence rows; never manufacture missing values."""
    rows=[]
    for s in snapshots:
        row=asdict(s)
        row["evidence_completeness"]=completeness(s)
        row["verified_market_data"]=bool(s.source_url and s.verified_at)
        row["missing_fields"]=[
            f for f in ("observed_price","demand_score","competition_score","shipping_cost","tariff_rate")
            if getattr(s,f) is None
        ]
        rows.append(row)
    return sorted(rows,key=lambda r:(not r["verified_market_data"],-r["evidence_completeness"]))

def market_unit_economics(snapshot: MarketSnapshot, product_cost: float) -> dict[str,Any]:
    if snapshot.observed_price is None:
        return {"status":"INSUFFICIENT_EVIDENCE","reason":"observed_price_missing"}
    if snapshot.shipping_cost is None or snapshot.tariff_rate is None:
        return {"status":"INSUFFICIENT_EVIDENCE","reason":"shipping_or_tariff_missing"}
    landed=product_cost+snapshot.shipping_cost+(product_cost+snapshot.shipping_cost)*snapshot.tariff_rate
    return {
        "status":"CALCULATED",
        "market":snapshot.market,
        "sale_price":snapshot.observed_price,
        "landed_cost":round(landed,2),
        "gross_profit":round(snapshot.observed_price-landed,2),
        "gross_margin":round((snapshot.observed_price-landed)/snapshot.observed_price,4)
            if snapshot.observed_price else 0,
    }
