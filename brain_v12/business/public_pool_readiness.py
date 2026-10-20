"""Secret-safe readiness checks for a manually configured Public Pool worker.

This module never starts a miner, opens a network connection, reads credentials,
or prints the payout address. It only checks local configuration presence and
returns an explicit non-execution status.
"""
from __future__ import annotations

import os
import re
from typing import Mapping, Any

PUBLIC_POOL_ENDPOINTS = {
    "solo": {
        "stratum_v1": "stratum+tcp://public-pool.io:3333",
        "stratum_tls": "stratum+tls://public-pool.io:4333",
        "cpuminer_tls": "stratum+tcps://public-pool.io:4333",
    },
    "pplns": {
        "stratum_v1": "stratum+tcp://public-pool.io:13333",
        "stratum_tls": "stratum+tls://public-pool.io:14333",
        "cpuminer_tls": "stratum+tcps://public-pool.io:14333",
    },
}
PUBLIC_POOL_DATUM_ENDPOINT = "datum://public-pool.io:23336"
PUBLIC_POOL_DATUM_KEY_REQUIRED = True
_PUBLIC_BTC_ADDRESS = re.compile(
    r"^(?:bc1[ac-hj-np-z02-9]{11,71}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})$",
    re.IGNORECASE,
)
_WORKER_NAME = re.compile(r"^[A-Za-z0-9_-]{1,32}$")


def assess_public_pool_readiness(env: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Assess local config without network access or mining side effects."""
    source = os.environ if env is None else env
    address = source.get("BRAIN_MINING_PAYOUT_ADDRESS", "").strip()
    worker = source.get("BRAIN_MINING_WORKER_NAME", "Realme01").strip()
    mode = source.get("BRAIN_PUBLIC_POOL_MODE", "pplns").strip().lower()
    mode_valid = mode in PUBLIC_POOL_ENDPOINTS
    selected = PUBLIC_POOL_ENDPOINTS.get(mode, PUBLIC_POOL_ENDPOINTS["pplns"])

    address_present = bool(address)
    address_shape_valid = bool(_PUBLIC_BTC_ADDRESS.fullmatch(address)) if address else False
    worker_valid = bool(_WORKER_NAME.fullmatch(worker))
    ready = address_shape_valid and worker_valid and mode_valid

    return {
        "pool": "Public Pool",
        "mode": mode if mode_valid else "invalid",
        "stratum_url": selected["stratum_v1"],
        "stratum_tls_url": selected["stratum_tls"],
        "cpuminer_tls_url": selected["cpuminer_tls"],
        "payout_address_configured": address_present,
        "payout_address_shape_valid": address_shape_valid,
        "worker_name": worker,
        "worker_name_valid": worker_valid,
        "mode_valid": mode_valid,
        "ready_for_manual_review": ready,
        "miner_started": False,
        "network_connection_attempted": False,
        "accepted_shares_verified": False,
        "revenue_realized": False,
        "status": "READY_FOR_MANUAL_REVIEW" if ready else "BLOCKED_CONFIGURATION",
        "required_environment": [
            "BRAIN_MINING_PAYOUT_ADDRESS",
            "BRAIN_MINING_WORKER_NAME (optional; defaults to Realme01)",
            "BRAIN_PUBLIC_POOL_MODE (optional; solo or pplns; defaults to pplns)",
        ],
    }
