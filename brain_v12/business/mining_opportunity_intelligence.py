"""Mining Opportunity Intelligence.

Combines validated public market evidence, normalized Braiins worker telemetry,
and the evidence-first economics engine into one read-only decision snapshot.
It never logs into providers, purchases hashpower, changes worker settings,
withdraws funds, or declares realized revenue.
"""
from __future__ import annotations

from typing import Any

from .braiins_readonly_adapter import parse_braiins_workers_response
from .crypto_market_snapshot import MarketSnapshot
from .mining_economics_engine import build_mining_economics_engine_report
from .mining_economics_gate import MiningEconomicsInput


def build_mining_opportunity_report(
    *,
    braiins_payload: dict[str, Any],
    market: MarketSnapshot,
    electricity_usd_kwh: float,
    efficiency_j_th: float,
    pool_fee_pct: float = 2.5,
    uptime_pct: float = 95.0,
    other_daily_cost_usd: float = 0.0,
) -> dict[str, Any]:
    """Build a deterministic opportunity report from supplied evidence."""
    workers = parse_braiins_workers_response(braiins_payload)
    market.validate(max_age_hours=24.0)

    worker_reports: list[dict[str, Any]] = []
    for item in workers:
        telemetry = item["telemetry"]
        hashrate = float(getattr(telemetry, "hashrate_th", 0.0))
        if hashrate <= 0:
            continue
        inp = MiningEconomicsInput(
            hashrate_th=hashrate,
            hashprice_usd_per_th_day=market.hashprice_usd_per_th_day,
            electricity_usd_kwh=electricity_usd_kwh,
            efficiency_j_th=efficiency_j_th,
            uptime_pct=uptime_pct,
            pool_fee_pct=pool_fee_pct,
            other_daily_cost_usd=other_daily_cost_usd,
            market_source=market.source,
            observation_age_hours=0.0,
        )
        economics = build_mining_economics_engine_report(
            inp,
            electricity_scenarios=(
                max(0.0, electricity_usd_kwh * 0.75),
                electricity_usd_kwh,
                electricity_usd_kwh * 1.25,
            ),
            hashprice_multipliers=(0.75, 1.0, 1.25),
        )
        worker_reports.append({
            "worker_id": item["worker_id"],
            "evidence": item["evidence"],
            "economics": economics,
        })

    return {
        "engine": "Brain Mining Opportunity Intelligence",
        "version": "1.0",
        "market_evidence": {
            "asset": market.asset,
            "hashprice_usd_per_th_day": market.hashprice_usd_per_th_day,
            "observed_at": market.observed_at,
            "source": market.source,
            "btc_price_usd": market.btc_price_usd,
            "network_hashrate_eh": market.network_hashrate_eh,
            "difficulty": market.difficulty,
            "evidence_urls": list(market.evidence_urls),
        },
        "workers": worker_reports,
        "decision_policy": {
            "read_only": True,
            "auto_purchase": False,
            "auto_contract": False,
            "auto_withdrawal": False,
            "funds_moved_by_brain": False,
            "revenue_realized": False,
            "human_approval_required_for_external_action": True,
        },
    }
