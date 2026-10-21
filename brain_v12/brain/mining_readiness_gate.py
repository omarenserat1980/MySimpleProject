"""Fail-closed evidence gate for real mining readiness.

This module classifies evidence only. It never starts miners, authorizes Stratum
workers, submits shares, changes pool settings, or labels telemetry as revenue.
"""
from __future__ import annotations

from typing import Any

SCHEMA = "electronic-brain.mining-readiness-gate.v1"


def evaluate_mining_readiness(
    *,
    asic_status: dict[str, Any] | None = None,
    ckpool_evidence: dict[str, Any] | None = None,
    payout_address_configured: bool = False,
) -> dict[str, Any]:
    """Return evidence-based blockers; missing or ambiguous evidence fails closed."""
    asic = asic_status if isinstance(asic_status, dict) else {}
    ck = ckpool_evidence if isinstance(ckpool_evidence, dict) else {}
    telemetry = ck.get("pool_telemetry") if isinstance(ck.get("pool_telemetry"), dict) else {}
    probe = ck.get("stratum_probe") if isinstance(ck.get("stratum_probe"), dict) else {}

    blockers: list[str] = []
    if asic.get("state") != "READ_ONLY_DATA_RECEIVED" or asic.get("device_contacted") is False:
        blockers.append("ASIC_READ_ONLY_DEVICE_EVIDENCE_MISSING")
    asic_telemetry = asic.get("telemetry") if isinstance(asic.get("telemetry"), dict) else {}
    has_hashrate = asic_telemetry.get("reported_hashrate") not in (None, "", 0, 0.0)
    if not has_hashrate:
        blockers.append("LOCAL_HASHRATE_NOT_VERIFIED")
    if not probe.get("tcp_connected") or not probe.get("subscription_response_present"):
        blockers.append("STRATUM_REACHABILITY_NOT_VERIFIED")
    if not payout_address_configured:
        blockers.append("PAYOUT_ADDRESS_NOT_CONFIGURED")
    if not telemetry.get("local_share_acceptance_verified"):
        blockers.append("ACCEPTED_SHARES_NOT_VERIFIED")
    if not ck.get("block_found_verified"):
        blockers.append("BLOCK_REWARD_NOT_VERIFIED")
    if not ck.get("payout_verified"):
        blockers.append("PAYOUT_NOT_VERIFIED")

    # A positive readiness result is deliberately not equivalent to mining or revenue.
    return {
        "schema": SCHEMA,
        "state": "BLOCKED" if blockers else "EVIDENCE_REVIEW_REQUIRED",
        "readiness_for_real_mining": False,
        "real_mining_verified": False,
        "revenue_realized": False,
        "financial_execution_enabled": False,
        "blockers": blockers,
        "evidence_inputs": {
            "asic_read_only_status_supplied": bool(asic),
            "ckpool_evidence_supplied": bool(ck),
            "payout_address_configured": bool(payout_address_configured),
        },
        "side_effects": {
            "network_scan_performed": False,
            "miner_started": False,
            "stratum_authorization_sent": False,
            "shares_submitted": False,
            "pool_settings_changed": False,
            "funds_moved": False,
        },
        "note": "This gate classifies supplied evidence only; it does not authorize mining or prove income.",
    }
