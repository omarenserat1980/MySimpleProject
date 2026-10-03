"""Read-only Braiins Pool API response normalization.

This module does not perform network calls, authenticate, control workers,
request payouts, or move funds. It converts documented API payloads into
Brain evidence structures for an audited HTTP client.
"""
from __future__ import annotations

from typing import Any

from .crypto_worker_telemetry import normalize_braiins_worker


def _object(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an object")
    return value


def parse_braiins_workers_response(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize the documented /accounts/workers/json/btc response."""
    root = _object(payload, "payload")
    btc = _object(root.get("btc"), "btc")
    workers = _object(btc.get("workers"), "workers")
    result: list[dict[str, Any]] = []
    for worker_id, worker_payload in workers.items():
        telemetry = normalize_braiins_worker(str(worker_id), worker_payload)
        result.append({
            "worker_id": telemetry.worker_id,
            "telemetry": telemetry,
            "evidence": {
                "type": "worker_telemetry",
                "worker_id": telemetry.worker_id,
                "source": telemetry.source,
                "observed_at": telemetry.observed_at,
                "proof_level": "MINING_EVIDENCE_ONLY",
                "payout_verified": False,
                "revenue_realized": False,
            },
        })
    return result


def parse_braiins_payouts_response(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize documented payout records without declaring revenue realized."""
    root = _object(payload, "payload")
    onchain = root.get("onchain", [])
    if not isinstance(onchain, list):
        raise ValueError("onchain must be a list")
    result: list[dict[str, Any]] = []
    for payout in onchain:
        record = _object(payout, "payout")
        try:
            amount = int(record.get("amount_sats"))
        except (TypeError, ValueError) as exc:
            raise ValueError("amount_sats must be an integer") from exc
        if amount < 0:
            raise ValueError("amount_sats must be non-negative")
        result.append({
            "status": str(record.get("status", "")).strip().lower(),
            "amount_sats": amount,
            "tx_id": str(record.get("tx_id", "")).strip(),
            "destination": str(record.get("destination", "")).strip(),
            "requested_at_ts": record.get("requested_at_ts"),
            "resolved_at_ts": record.get("resolved_at_ts"),
            "fee_sats": record.get("fee_sats", 0),
            "proof_level": "PAYOUT_EVIDENCE_ONLY",
            "revenue_realized": False,
        })
    return result
