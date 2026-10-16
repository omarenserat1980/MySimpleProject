"""Evidence-first, read-only diagnosis for Brain's Braiins Pool integration.

This module classifies sanitized observations collected by trusted diagnostics.
It performs no network calls, reads no credentials, starts no miner, and cannot
promote simulated telemetry to proof of mining.
"""
from __future__ import annotations

from typing import Any


def classify_braiins_diagnostics(observation: dict[str, Any]) -> dict[str, Any]:
    """Classify the most actionable blocker from sanitized diagnostic facts.

    Expected optional fields:
      miner_process_found: bool
      dns_ok: bool
      tcp_ok: bool
      pool_worker_count: non-negative int
      hashrate_hs: non-negative number
      accepted_shares: non-negative int
      stratum_authorized: bool

    Missing or malformed fields are treated as unknown, never as success.
    """
    if not isinstance(observation, dict):
        observation = {}

    def flag(name: str) -> bool | None:
        value = observation.get(name)
        return value if isinstance(value, bool) else None

    def count(name: str) -> int | None:
        value = observation.get(name)
        if isinstance(value, bool):
            return None
        if isinstance(value, int) and value >= 0:
            return value
        return None

    def number(name: str) -> float | None:
        value = observation.get(name)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        if value < 0:
            return None
        return float(value)

    process = flag("miner_process_found")
    dns_ok = flag("dns_ok")
    tcp_ok = flag("tcp_ok")
    authorized = flag("stratum_authorized")
    workers = count("pool_worker_count")
    shares = count("accepted_shares")
    hashrate = number("hashrate_hs")

    state = "INSUFFICIENT_EVIDENCE"
    next_action = "Collect missing read-only observations on the authorized mining host."
    if process is False:
        state = "NO_MINER_PROCESS"
        next_action = "Identify the intended miner application; do not install or launch one automatically."
    elif dns_ok is False:
        state = "DNS_FAILURE"
        next_action = "Investigate DNS resolution on the mining host; do not change firewall rules."
    elif tcp_ok is False:
        state = "STRATUM_TCP_UNREACHABLE"
        next_action = "Inspect the host's outbound network path and logs; do not open ports blindly."
    elif authorized is False:
        state = "STRATUM_AUTHORIZATION_FAILED"
        next_action = "Inspect the miner's redacted authorization log and worker-name format."
    elif workers == 0:
        state = "NO_POOL_WORKERS"
        next_action = "Verify the pool account and worker name using read-only evidence."
    elif workers is not None and workers > 0 and shares == 0:
        if hashrate == 0:
            state = "WORKER_PRESENT_NO_HASHRATE_OR_SHARES"
            next_action = "Inspect miner logs and pool-side worker state; no accepted work is verified."
        else:
            state = "HASHRATE_REPORTED_NO_ACCEPTED_SHARES"
            next_action = "Compare pool-side accepted shares with miner logs; hashrate alone is insufficient."
    elif workers is not None and workers > 0 and shares is not None and shares > 0:
        state = "POOL_ACCEPTED_SHARES_OBSERVED"
        next_action = "Cross-check fresh pool telemetry independently; this is not proof of payout or profitability."
    return {
        "ok": True,
        "diagnostic_only": True,
        "state": state,
        "real_mining_verified": False,
        "revenue_realized": False,
        "observations": {
            "miner_process_found": process,
            "dns_ok": dns_ok,
            "tcp_ok": tcp_ok,
            "stratum_authorized": authorized,
            "pool_worker_count": workers,
            "hashrate_hs": hashrate,
            "accepted_shares": shares,
        },
        "next_action": next_action,
        "secrets_collected": False,
        "production_settings_changed": False,
    }
