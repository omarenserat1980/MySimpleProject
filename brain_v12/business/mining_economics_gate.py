"""Evidence-first mining economics gate.

This module classifies a mining opportunity from measured assumptions. It never
purchases hashpower, changes provider settings, moves funds, or declares
revenue. Positive arithmetic is not a promise of profitability.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class MiningEconomicsInput:
    hashrate_th: float
    hashprice_usd_per_th_day: float
    electricity_usd_kwh: float
    efficiency_j_th: float
    uptime_pct: float = 100.0
    pool_fee_pct: float = 2.5
    other_daily_cost_usd: float = 0.0
    hardware_or_hashpower_cost_usd: float = 0.0
    observation_age_hours: float = 0.0
    market_source: str = ""

    def validate(self) -> None:
        if self.hashrate_th <= 0 or self.hashprice_usd_per_th_day <= 0:
            raise ValueError("hashrate and hashprice must be > 0")
        if self.electricity_usd_kwh < 0 or self.efficiency_j_th <= 0:
            raise ValueError("electricity and efficiency are invalid")
        if not 0 < self.uptime_pct <= 100:
            raise ValueError("uptime_pct must be in (0, 100]")
        if not 0 <= self.pool_fee_pct < 100:
            raise ValueError("pool_fee_pct must be in [0, 100)")
        if self.other_daily_cost_usd < 0 or self.hardware_or_hashpower_cost_usd < 0:
            raise ValueError("costs must be >= 0")
        if self.observation_age_hours < 0:
            raise ValueError("observation_age_hours must be >= 0")


def evaluate_mining_economics(inp: MiningEconomicsInput) -> dict[str, Any]:
    inp.validate()
    uptime = inp.uptime_pct / 100.0
    gross = inp.hashrate_th * inp.hashprice_usd_per_th_day * uptime
    pool_fee = gross * inp.pool_fee_pct / 100.0
    power_kw = inp.hashrate_th * inp.efficiency_j_th / 1000.0
    kwh_day = power_kw * 24.0 * uptime
    electricity = kwh_day * inp.electricity_usd_kwh
    net = gross - pool_fee - electricity - inp.other_daily_cost_usd
    break_even = (
        (gross - pool_fee - inp.other_daily_cost_usd) / kwh_day
        if kwh_day else 0.0
    )

    if not inp.market_source or inp.observation_age_hours > 24:
        status = "UNCERTAIN"
    elif net > 0:
        status = "ECONOMICALLY_PLAUSIBLE"
    elif net < 0:
        status = "NOT_ECONOMIC"
    else:
        status = "UNCERTAIN"

    return {
        "status": status,
        "gross_daily_revenue_usd": round(gross, 6),
        "pool_fee_daily_usd": round(pool_fee, 6),
        "electricity_kwh_daily": round(kwh_day, 6),
        "electricity_cost_daily_usd": round(electricity, 6),
        "other_daily_cost_usd": round(inp.other_daily_cost_usd, 6),
        "net_daily_cashflow_usd": round(net, 6),
        "break_even_electricity_usd_kwh": round(max(break_even, 0.0), 6),
        "simple_30d_cashflow_usd": round(net * 30.0, 6),
        "simple_payback_days": (
            round(inp.hardware_or_hashpower_cost_usd / net, 2)
            if inp.hardware_or_hashpower_cost_usd > 0 and net > 0 else None
        ),
        "assumptions": asdict(inp),
        "guardrails": {
            "auto_purchase": False,
            "auto_contract": False,
            "auto_withdrawal": False,
            "funds_moved_by_brain": False,
            "revenue_realized": False,
            "human_approval_required_for_external_action": True,
        },
    }
