"""Financial intelligence layer for the Electronic Brain.

Three evidence-based layers:
1. Unit economics: revenue, direct cost, hours, net profit and margin.
2. Cash-flow discipline: reserves, runway and liquidity risk.
3. Credit/transaction safety: affordability limits and verified-payment states.

These are decision rules, not financial advice or guaranteed returns.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any
import math


@dataclass
class UnitEconomics:
    price_jod: float
    direct_cost_jod: float
    hours: float

    @property
    def gross_profit_jod(self) -> float:
        return round(self.price_jod - self.direct_cost_jod, 2)

    @property
    def margin(self) -> float:
        return round(self.gross_profit_jod / max(self.price_jod, 0.01), 4)

    @property
    def hourly_profit_jod(self) -> float:
        return round(self.gross_profit_jod / max(self.hours, 0.25), 2)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self) | {
            "gross_profit_jod": self.gross_profit_jod,
            "margin": self.margin,
            "hourly_profit_jod": self.hourly_profit_jod,
        }


def score_unit_economics(price_jod: float, direct_cost_jod: float, hours: float) -> dict[str, Any]:
    unit = UnitEconomics(float(price_jod), float(direct_cost_jod), float(hours))
    return unit.to_dict()


def cash_runway(cash_jod: float, fixed_monthly_cost_jod: float) -> dict[str, Any]:
    cash = max(float(cash_jod), 0.0)
    burn = max(float(fixed_monthly_cost_jod), 0.0)
    months = math.inf if burn == 0 else round(cash / burn, 2)
    return {"cash_jod": round(cash, 2), "monthly_burn_jod": round(burn, 2), "runway_months": months}


def safe_commitment_limit(cash_jod: float, reserve_ratio: float = 0.30) -> float:
    """Maximum discretionary commitment under a configurable reserve rule."""
    cash = max(float(cash_jod), 0.0)
    reserve = min(max(float(reserve_ratio), 0.0), 0.95)
    return round(cash * (1.0 - reserve), 2)


def evaluate_transaction(expected_revenue_jod: float, direct_cost_jod: float,
                         hours: float, payment_verified: bool = False) -> dict[str, Any]:
    unit = UnitEconomics(float(expected_revenue_jod), float(direct_cost_jod), float(hours))
    return {
        "economics": unit.to_dict(),
        "expected_net_jod": unit.gross_profit_jod,
        "payment_status": "VERIFIED" if payment_verified else "UNVERIFIED",
        "counts_as_realized_profit": bool(payment_verified and unit.gross_profit_jod > 0),
    }
