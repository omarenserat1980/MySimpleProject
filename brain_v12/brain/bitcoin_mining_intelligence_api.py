"""Bitcoin Mining Intelligence: zero-capital, simulation-first analysis for Electronic Brain."""
from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .mining_engine import MiningEngine
from .bitcoin_hash_benchmark import benchmark_header_hashing

router = APIRouter(prefix="/api/bitcoin-mining", tags=["Bitcoin Mining Intelligence"])
engine = MiningEngine()


class MiningAnalysisRequest(BaseModel):
    algorithm: str = "SHA-256"
    hashrate: float = Field(ge=0)
    hashrate_unit: str
    power_watts: float = Field(ge=0)
    electricity_jod_per_kwh: float = Field(ge=0)
    gross_revenue_jod_per_day: float = Field(ge=0)
    hardware_cost_jod: float = Field(default=0, ge=0)
    pool_fee_percent: float = Field(default=0, ge=0, lt=100)
    other_daily_cost_jod: float = Field(default=0, ge=0)


@router.get("/status")
def _configured_capital_budget_jod() -> float:
    """Zero is the default starting budget, not a permanent income ceiling."""
    try:
        value = float(os.getenv("BRAIN_CAPITAL_BUDGET_JOD", "0"))
    except (TypeError, ValueError):
        return 0.0
    return value if value >= 0 else 0.0


def bitcoin_mining_status() -> dict[str, Any]:
    capital_budget = _configured_capital_budget_jod()
    paid_mining_authorized = os.getenv("BRAIN_ALLOW_PAID_MINING", "0").strip() == "1" and capital_budget > 0
    return {
        "ok": True,
        "module": "Bitcoin Mining Intelligence",
        "status": "READY",
        "execution_mode": "ANALYSIS_AND_DRY_RUN_ONLY",
        "income_objective": "maximize verified net income; zero budget is a starting condition, not a permanent target",
        "capital_budget_jod": capital_budget,
        "capital_budget_source": "BRAIN_CAPITAL_BUDGET_JOD environment setting; defaults to 0",
        "zero_upfront_cost_priority": capital_budget <= 0,
        "real_mining_enabled": False,
        "real_mining_blocker": "NO_VERIFIED_PHYSICAL_MINING_ADAPTER",
        "wallet_access": False,
        "paid_cloud_mining_allowed": paid_mining_authorized,
        "paid_cloud_mining_policy": "requires BRAIN_ALLOW_PAID_MINING=1 and positive configured budget; never enabled by profitability estimates alone",
        "live_market_data": False,
        "asic_simulator": "/api/asic-sim/status",
        "verified_revenue_jod": 0.0,
        "reality_note": "ASIC software simulation is not real ASIC hashing and does not earn BTC.",
    }


@router.post("/analyze")
def bitcoin_mining_analyze(body: MiningAnalysisRequest) -> dict[str, Any]:
    """Calculate economics from explicitly supplied assumptions; never imply live data."""
    try:
        result = engine.analyze(body.dict())
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    result["intelligence"] = {
        "recommendation": "REVIEW_INPUTS",
        "zero_capital_policy": "PASS" if body.hardware_cost_jod == 0 and body.other_daily_cost_jod == 0 else "BLOCKED_NONZERO_COST",
        "execution_authorized": False,
        "evidence_required_for_income": True,
    }
    return result


@router.post("/plan")
def bitcoin_mining_plan(body: MiningAnalysisRequest) -> dict[str, Any]:
    """Create a safe plan only. This endpoint never starts a miner or connects a wallet."""
    analysis = bitcoin_mining_analyze(body)
    profitable_on_inputs = analysis.get("net_jod_per_day", 0) > 0
    # Zero-capital means no upfront hardware purchase. Operating costs remain in
    # the net-profit calculation; they must not be confused with capital spend.
    zero_cost = body.hardware_cost_jod == 0
    return {
        "ok": True,
        "status": "BLOCKED_REVENUE_UNVERIFIED" if profitable_on_inputs and zero_cost else "BLOCKED",
        "profit_gate": analysis.get("profit_gate", engine.profit_gate()),
        "mode": "DRY_RUN",
        "stages": [
            {"name": "INPUT_VALIDATION", "status": "PASS"},
            {"name": "ECONOMICS_ANALYSIS", "status": "PASS"},
            {"name": "ZERO_UPFRONT_CAPITAL_GATE", "status": "PASS" if zero_cost else "BLOCKED"},
            {"name": "REAL_HARDWARE_ATTESTATION", "status": "BLOCKED_NOT_CONFIGURED"},
            {"name": "MINING_EXECUTION", "status": "DISABLED"},
            {"name": "REVENUE_VERIFICATION", "status": "NOT_ESTABLISHED"},
        ],
        "analysis": analysis,
        "spend_authorized": False,
        "real_mining_started": False,
        "verified_revenue_jod": 0.0,
        "next_step": "Find and validate the highest-value no-upfront-cost path first. Real mining remains blocked only because a verified physical adapter and independent pool/payout evidence are not connected; this endpoint never starts mining.",
    }



class HashBenchmarkRequest(BaseModel):
    duration_seconds: float = Field(default=1.0, ge=0.05, le=3.0)
    max_hashes: int = Field(default=100000, ge=1, le=100000)


@router.post("/benchmark")
def bitcoin_mining_benchmark(body: HashBenchmarkRequest) -> dict[str, Any]:
    """Run a bounded local SHA-256d CPU benchmark; never starts live mining."""
    try:
        result = benchmark_header_hashing(
            duration_seconds=body.duration_seconds,
            max_hashes=body.max_hashes,
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return result
