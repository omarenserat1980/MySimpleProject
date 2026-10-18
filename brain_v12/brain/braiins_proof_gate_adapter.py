"""Translate real Braiins read-only telemetry into narrowly scoped proof envelopes.

This adapter never invents per-share acceptance, Brain-origin work, payout, or revenue
proof. Aggregate pool telemetry can satisfy only pool_connection and observed_hashrate.
"""
from __future__ import annotations

from typing import Any, Mapping


def braiins_telemetry_to_proof_records(result: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return only proof records justified by a successful live HTTPS snapshot.

    Test fixtures, blocked responses, stale observations, and incomplete provenance
    produce no proof records. The caller must still evaluate them with ProofGateEngine.
    """
    if not isinstance(result, Mapping):
        return []
    if (
        result.get("ok") is not True
        or result.get("status") != "POOL_ACTIVITY_OBSERVED"
        or result.get("pool_activity_verified") is not True
        or result.get("pool_source_authenticated_over_https") is not True
        or result.get("evidence_origin") != "LIVE_HTTPS_RESPONSE"
        or result.get("proof_level") != "INDEPENDENT_POOL_API_AGGREGATE_TELEMETRY"
    ):
        return []

    digest = result.get("pool_response_sha256")
    observed_at = result.get("observed_at_utc")
    worker_id = result.get("worker_id")
    hashrate = result.get("hashrate_5m_provider_units")
    unit = result.get("hashrate_unit")
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(ch not in "0123456789abcdef" for ch in digest)
        or not isinstance(observed_at, str)
        or not observed_at.strip()
        or not isinstance(worker_id, str)
        or not worker_id.strip()
        or isinstance(hashrate, bool)
        or not isinstance(hashrate, (int, float))
        or hashrate <= 0
        or not isinstance(unit, str)
        or not unit.strip()
    ):
        return []

    common = {
        "source_type": "braiins_pool_readonly_api",
        "observed_at": observed_at,
        "status": "VERIFIED",
        "environment": "production",
        "artifact_sha256": digest,
        "source_reference": "https://pool.braiins.com/accounts/workers/json/btc",
        "worker_id": worker_id,
        "limitations": [
            "Aggregate pool telemetry is not per-share acceptance evidence.",
            "This does not prove Brain produced the work.",
            "This does not prove payout or realized revenue.",
        ],
    }
    return [
        {
            **common,
            "evidence_id": f"braiins-pool-connection:{digest}",
            "proof_type": "pool_connection",
        },
        {
            **common,
            "evidence_id": f"braiins-observed-hashrate:{digest}",
            "proof_type": "observed_hashrate",
            "hashrate_5m_provider_units": hashrate,
            "hashrate_unit": unit,
        },
    ]
