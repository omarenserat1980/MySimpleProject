"""Final fail-closed gate for Bitcoin mining revenue evidence."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RevenueEvidence:
    worker_authorized: bool
    pool_connected: bool
    accepted_shares: int
    payout_observed: bool
    payout_txid: str | None = None
    btc_received: float = 0.0


def evaluate(evidence: RevenueEvidence) -> dict:
    checks = {
        "worker_authorized": evidence.worker_authorized,
        "pool_connected": evidence.pool_connected,
        "accepted_shares": evidence.accepted_shares > 0,
        "payout_observed": evidence.payout_observed,
        "btc_received": evidence.btc_received > 0 and bool(evidence.payout_txid),
    }
    if not all(checks.values()):
        return {
            "status": "BLOCKED",
            "revenue_realized": False,
            "checks": checks,
            "next_action": "provide_missing_real_world_evidence",
        }
    return {
        "status": "REVENUE_REALIZED",
        "revenue_realized": True,
        "checks": checks,
        "payout_txid": evidence.payout_txid,
        "btc_received": evidence.btc_received,
    }
