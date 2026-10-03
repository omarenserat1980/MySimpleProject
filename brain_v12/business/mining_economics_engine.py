"""Evidence-first Mining Economics Engine.

Builds a reproducible economic scenario report from the existing mining gate.
It performs analysis only: no provider changes, purchases, contracts,
withdrawals, or fund movement.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Any, Iterable

from .mining_economics_gate import MiningEconomicsInput, evaluate_mining_economics


def build_mining_economics_engine_report(
    inp: MiningEconomicsInput,
    *,
    electricity_scenarios: Iterable[float] = (),
    hashprice_multipliers: Iterable[float] = (),
) -> dict[str, Any]:
    """Return base economics plus deterministic sensitivity scenarios."""
    base = evaluate_mining_economics(inp)
    electricity = []
    for price in electricity_scenarios:
        if price < 0:
            raise ValueError("electricity scenario must be >= 0")
        scenario = evaluate_mining_economics(replace(inp, electricity_usd_kwh=price))
        electricity.append({
            "electricity_usd_kwh": price,
            "status": scenario["status"],
            "net_daily_cashflow_usd": scenario["net_daily_cashflow_usd"],
            "simple_30d_cashflow_usd": scenario["simple_30d_cashflow_usd"],
            "break_even_electricity_usd_kwh": scenario[
                "break_even_electricity_usd_kwh"
            ],
        })

    hashprice = []
    for multiplier in hashprice_multipliers:
        if multiplier <= 0:
            raise ValueError("hashprice multiplier must be > 0")
        scenario = evaluate_mining_economics(replace(
            inp,
            hashprice_usd_per_th_day=inp.hashprice_usd_per_th_day * multiplier,
        ))
        hashprice.append({
            "hashprice_multiplier": multiplier,
            "hashprice_usd_per_th_day": round(
                inp.hashprice_usd_per_th_day * multiplier, 9
            ),
            "status": scenario["status"],
            "net_daily_cashflow_usd": scenario["net_daily_cashflow_usd"],
            "simple_30d_cashflow_usd": scenario["simple_30d_cashflow_usd"],
        })

    return {
        "engine": "Brain Mining Economics Engine",
        "version": "1.0",
        "base": base,
        "sensitivity": {
            "electricity": electricity,
            "hashprice": hashprice,
        },
        "decision_policy": {
            "analysis_only": True,
            "auto_purchase": False,
            "auto_contract": False,
            "auto_withdrawal": False,
            "funds_moved_by_brain": False,
            "revenue_realized": False,
            "human_approval_required_for_external_action": True,
        },
    }
