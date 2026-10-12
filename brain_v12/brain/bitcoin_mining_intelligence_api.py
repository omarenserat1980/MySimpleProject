"""Bitcoin Mining Intelligence: zero-capital, simulation-first analysis for Electronic Brain."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .mining_engine import MiningEngine

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
def bitcoin_mining_status() -> dict[str, Any]:
    return {
        "ok": True,
        "module": "Bitcoin Mining Intelligence",
        "status": "READY",
        "execution_mode": "ANALYSIS_AND_DRY_RUN_ONLY",
        "capital_budget_jod": 0,
        "real_mining_enabled": False,
        "wallet_access": False,
        "paid_cloud_mining_allowed": False,
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
    zero_cost = body.hardware_cost_jod == 0 and body.other_daily_cost_jod == 0
    return {
        "ok": True,
        "status": "DRY_RUN_READY" if profitable_on_inputs and zero_cost else "BLOCKED",
        "mode": "DRY_RUN",
        "stages": [
            {"name": "INPUT_VALIDATION", "status": "PASS"},
            {"name": "ECONOMICS_ANALYSIS", "status": "PASS"},
            {"name": "ZERO_CAPITAL_GATE", "status": "PASS" if zero_cost else "BLOCKED"},
            {"name": "REAL_HARDWARE_ATTESTATION", "status": "BLOCKED_NOT_CONFIGURED"},
            {"name": "MINING_EXECUTION", "status": "DISABLED"},
            {"name": "REVENUE_VERIFICATION", "status": "NOT_ESTABLISHED"},
        ],
        "analysis": analysis,
        "spend_authorized": False,
        "real_mining_started": False,
        "verified_revenue_jod": 0.0,
        "next_step": "Connect a real, independently verified ASIC and reliable market/pool data before reconsidering execution; never use paid cloud resources under the zero-capital policy.",
    }
