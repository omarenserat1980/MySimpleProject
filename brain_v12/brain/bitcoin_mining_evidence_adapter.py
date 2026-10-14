"""Adapter from independently sourced worker telemetry into the fail-closed gate.

The Stratum probe proves connection/authorization only. Hashrate and share
counters must come from separately configured, allow-listed telemetry sources.
This adapter does not verify payouts or revenue.
"""
from __future__ import annotations

from typing import Any, Iterable

from brain_v12.brain.bitcoin_mining_evidence_gate import (
    canonical_digest,
    validate_live_mining_evidence,
)


def build_mining_evidence_record(
    probe: dict[str, Any],
    *,
    worker_id: str,
    hashrate: dict[str, Any] | None,
    shares: dict[str, Any] | None,
    trusted_source_ids: Iterable[str],
    fixture: bool = False,
) -> dict[str, Any]:
    """Build a canonical record; missing or untrusted telemetry remains blocked.

    trusted_source_ids must be configured by the operator from known provider
    identities. Merely supplying a source string is not cryptographic proof of
    provenance; callers must authenticate the telemetry before calling here.
    """
    trusted = {item for item in trusted_source_ids if isinstance(item, str) and item.strip()}
    if not isinstance(probe, dict):
        raise ValueError("STRATUM_PROBE_EVIDENCE_REQUIRED")
    if probe.get("mode") != "connection_probe_only":
        raise ValueError("UNEXPECTED_STRATUM_PROBE_MODE")
    if probe.get("protocol") != "stratum-v1" or probe.get("subscribed") is not True or probe.get("authorized") is not True:
        raise ValueError("STRATUM_CONNECTION_AND_AUTHORIZATION_REQUIRED")
    if not isinstance(worker_id, str) or not worker_id.strip():
        raise ValueError("WORKER_ID_REQUIRED")
    if not isinstance(hashrate, dict) or hashrate.get("source") not in trusted:
        raise ValueError("HASHRATE_SOURCE_NOT_TRUSTED")
    if not isinstance(shares, dict) or shares.get("source") not in trusted:
        raise ValueError("SHARE_SOURCE_NOT_TRUSTED")
    observed = probe.get("observed_at_utc")
    host = probe.get("pool_host")
    port = probe.get("pool_port")
    if not isinstance(observed, str) or not isinstance(host, str) or not host.strip():
        raise ValueError("STRATUM_PROBE_METADATA_MISSING")
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise ValueError("STRATUM_POOL_PORT_INVALID")

    record = {
        "schema_version": "1.0",
        "mode": "live",
        "fixture": fixture is True,
        "worker_id": worker_id,
        "observed_at_utc": observed,
        "pool": {
            "host": host,
            "port": port,
            "protocol": "stratum",
            "connected": True,
            "authorized": True,
            "connected_at_utc": observed,
            "source": "bitcoin_stratum_connection_probe",
        },
        "hashrate": dict(hashrate),
        "shares": dict(shares),
    }
    record["evidence_artifact_sha256"] = canonical_digest(record)
    return record


def evaluate_mining_evidence(
    probe: dict[str, Any],
    *,
    worker_id: str,
    hashrate: dict[str, Any] | None,
    shares: dict[str, Any] | None,
    trusted_source_ids: Iterable[str],
    fixture: bool = False,
) -> dict[str, Any]:
    """Return gate result and keep payout/revenue explicitly unverified."""
    try:
        record = build_mining_evidence_record(
            probe,
            worker_id=worker_id,
            hashrate=hashrate,
            shares=shares,
            trusted_source_ids=trusted_source_ids,
            fixture=fixture,
        )
    except (TypeError, ValueError) as exc:
        return {
            "status": "BLOCKED",
            "gate": "MINING_ACTIVITY_VERIFIED",
            "failures": [str(exc)],
            "revenue_status": "UNVERIFIED",
            "execution_authorized": False,
        }
    result = validate_live_mining_evidence(record)
    result["revenue_status"] = "UNVERIFIED"
    result["execution_authorized"] = False
    return result
