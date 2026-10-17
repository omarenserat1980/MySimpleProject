"""Profit-first policy engine for Electronic Brain.

This module makes financial opportunity the default planning objective without
pretending that simulated telemetry is real revenue or bypassing device safety.
It audits blockers, computes conservative net profitability when inputs are
verified, and distinguishes a requested ASIC execution mode from proof that
mining is actually running.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class ProfitInputs:
    """All monetary values use one caller-selected fiat currency per day."""
    expected_gross_revenue_per_day: float | None
    electricity_cost_per_day: float | None
    pool_fee_per_day: float = 0.0
    other_cost_per_day: float = 0.0
    inputs_verified: bool = False
    device_connected: bool = False
    pool_authorized: bool = False
    payout_destination_configured: bool = False
    hardware_safe: bool = False
    explicit_execution_authorization: bool = False


def evaluate_profit(inputs: ProfitInputs) -> dict[str, Any]:
    """Return a transparent decision; unknown values never become fake profit."""
    blockers: list[str] = []
    if inputs.expected_gross_revenue_per_day is None:
        blockers.append("MISSING_REVENUE_ESTIMATE")
    if inputs.electricity_cost_per_day is None:
        blockers.append("MISSING_ELECTRICITY_COST")
    if not inputs.inputs_verified:
        blockers.append("UNVERIFIED_PROFIT_INPUTS")
    if not inputs.device_connected:
        blockers.append("ASIC_NOT_VERIFIED_CONNECTED")
    if not inputs.pool_authorized:
        blockers.append("POOL_NOT_AUTHORIZED")
    if not inputs.payout_destination_configured:
        blockers.append("PAYOUT_DESTINATION_NOT_CONFIGURED")
    if not inputs.hardware_safe:
        blockers.append("HARDWARE_SAFETY_NOT_VERIFIED")

    net: float | None = None
    if inputs.expected_gross_revenue_per_day is not None and inputs.electricity_cost_per_day is not None:
        net = (
            inputs.expected_gross_revenue_per_day
            - inputs.electricity_cost_per_day
            - inputs.pool_fee_per_day
            - inputs.other_cost_per_day
        )
    if net is None:
        status = "NEEDS_DATA"
    elif net <= 0:
        status = "NOT_PROFITABLE"
        blockers.append("NON_POSITIVE_NET_PROFIT")
    elif not inputs.inputs_verified:
        status = "UNVERIFIED_ESTIMATE"
    else:
        status = "PROFITABLE_ESTIMATE"

    execution_ready = (
        status == "PROFITABLE_ESTIMATE"
        and not blockers
        and inputs.explicit_execution_authorization
    )
    if status == "PROFITABLE_ESTIMATE" and not inputs.explicit_execution_authorization:
        blockers.append("EXPLICIT_EXECUTION_AUTHORIZATION_REQUIRED")

    return {
        "status": status,
        "currency_basis": "caller-specified; keep all inputs in the same currency",
        "gross_revenue_per_day": inputs.expected_gross_revenue_per_day,
        "electricity_cost_per_day": inputs.electricity_cost_per_day,
        "pool_fee_per_day": inputs.pool_fee_per_day,
        "other_cost_per_day": inputs.other_cost_per_day,
        "estimated_net_profit_per_day": net,
        "execution_ready": execution_ready,
        "blockers": sorted(set(blockers)),
        "evidence_class": "verified-input estimate" if inputs.inputs_verified else "unverified estimate",
        "warning": "A positive estimate is not proof of realized payouts.",
    }


def audit_profit_blockers(signals: dict[str, Any]) -> dict[str, Any]:
    """Identify system logic that obstructs earning, without disabling safeguards.

    Recognized policy signals should be supplied by adapters. Unknown/missing
    signals are reported as unknown rather than silently assumed healthy.
    """
    findings: list[dict[str, str]] = []
    checks = {
        "revenue_goal_configured": (
            "NO_REVENUE_OBJECTIVE",
            "No measurable income objective is configured; add a target and tracking period.",
        ),
        "profitability_gate_enabled": (
            "PROFIT_GATE_DISABLED",
            "Enable profitability checks before selecting mining or other income tasks.",
        ),
        "real_mining_adapter_available": (
            "NO_REAL_MINING_ADAPTER",
            "Implement and validate a device-specific ASIC adapter; a simulator is not a miner.",
        ),
        "pool_connection_verified": (
            "POOL_CONNECTION_UNVERIFIED",
            "Verify pool endpoint, worker identity, accepted shares, and pool-side hashrate.",
        ),
        "payout_evidence_available": (
            "NO_PAYOUT_EVIDENCE",
            "Track pool-account payouts and wallet receipts separately from estimated revenue.",
        ),
        "free_opportunity_scan_enabled": (
            "NO_FREE_OPPORTUNITY_SCAN",
            "Scan zero-upfront-cost opportunities first; never treat free as guaranteed profitable.",
        ),
    }
    for key, (code, message) in checks.items():
        value = signals.get(key)
        if value is False:
            findings.append({"code": code, "severity": "high", "message": message})
        elif value is None:
            findings.append({
                "code": f"UNKNOWN_{code}",
                "severity": "unknown",
                "message": f"Evidence missing for '{key}'; verify before claiming readiness.",
            })
    return {
        "objective": "maximize verified net income subject to authority, safety, and solvency constraints",
        "findings": findings,
        "findings_count": len(findings),
        "never_suppress": [
            "hardware overheating or electrical danger",
            "unauthorized pool or wallet access",
            "unverified earnings or simulated telemetry",
            "paid-resource commitments without explicit approval",
        ],
    }


def income_plan(current_budget: float = 0.0, target_budget: float = 1_000_000.0) -> dict[str, Any]:
    """Represent growth from zero as a staged goal, not a promise or forecast."""
    if current_budget < 0 or target_budget < 0:
        raise ValueError("budget and target must be non-negative")
    return {
        "current_budget": current_budget,
        "target_budget": target_budget,
        "remaining_gap": max(0.0, target_budget - current_budget),
        "stages": [
            {"name": "validate", "exit_condition": "real device/pool telemetry independently verified"},
            {"name": "first payout", "exit_condition": "small payout confirmed in pool and destination wallet"},
            {"name": "positive unit economics", "exit_condition": "net profit positive after electricity, pool fees, and all costs"},
            {"name": "reinvest carefully", "exit_condition": "reinvestment funded only from realized surplus"},
            {"name": "scale", "exit_condition": "repeatable positive net income with risk and cash-flow limits"},
        ],
        "guaranteed_income": 0.0,
        "note": "The target is aspirational; future income is not guaranteed.",
    }
