"""Mining telemetry normalization for user-owned pool workers.

This module converts public/documented pool telemetry shapes into a Brain
evidence record. It never authenticates, controls a worker, or claims payout.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class WorkerTelemetry:
    worker_id: str
    state: str
    hashrate_5m: float
    hashrate_60m: float
    hashrate_24h: float
    shares_5m: int
    shares_60m: int
    shares_24h: int
    last_share: int | None
    observed_at: str
    source: str


def _number(value: Any, field: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if result < 0:
        raise ValueError(f"{field} must be non-negative")
    return result


def _integer(value: Any, field: str) -> int:
    result = _number(value, field)
    if not result.is_integer():
        raise ValueError(f"{field} must be an integer")
    return int(result)


def normalize_braiins_worker(
    worker_id: str,
    payload: dict[str, Any],
    *,
    source: str = "braiins_pool_api",
) -> WorkerTelemetry:
    """Normalize the documented Braiins Pool worker object."""
    if not worker_id.strip():
        raise ValueError("worker_id is required")
    if not isinstance(payload, dict):
        raise ValueError("worker payload must be an object")

    state = str(payload.get("state", "")).strip().lower()
    if state not in {"ok", "low", "off", "dis"}:
        raise ValueError("unsupported worker state")

    return WorkerTelemetry(
        worker_id=worker_id,
        state=state,
        hashrate_5m=_number(payload.get("hash_rate_5m"), "hash_rate_5m"),
        hashrate_60m=_number(payload.get("hash_rate_60m"), "hash_rate_60m"),
        hashrate_24h=_number(payload.get("hash_rate_24h"), "hash_rate_24h"),
        shares_5m=_integer(payload.get("shares_5m"), "shares_5m"),
        shares_60m=_integer(payload.get("shares_60m"), "shares_60m"),
        shares_24h=_integer(payload.get("shares_24h"), "shares_24h"),
        last_share=_integer(payload["last_share"], "last_share") if payload.get("last_share") is not None else None,
        observed_at=datetime.now(timezone.utc).isoformat(),
        source=source,
    )


def evidence_from_telemetry(telemetry: WorkerTelemetry) -> dict[str, Any]:
    """Produce mining evidence without treating it as payout or revenue proof."""
    return {
        "type": "worker_telemetry",
        "worker_id": telemetry.worker_id,
        "source": telemetry.source,
        "observed_at": telemetry.observed_at,
        "telemetry": asdict(telemetry),
        "proof_level": "MINING_EVIDENCE_ONLY",
        "payout_verified": False,
        "revenue_realized": False,
    }
