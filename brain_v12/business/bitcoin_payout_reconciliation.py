"""Strict reconciliation of pool payout evidence with independently collected Bitcoin-chain data.

This module is deliberately a pure verifier: it makes no network calls, reads no
credentials, and cannot initiate mining or move funds. Callers must obtain the
two evidence records from their respective sources before invoking the audit.
"""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse
from datetime import datetime, timedelta, timezone
import re

_TXID = re.compile(r"^[0-9a-fA-F]{64}$")
_CHAIN_EXPLORER_HOSTS = {"mempool.space", "www.mempool.space", "blockstream.info", "www.blockstream.info"}


def _positive_int(value: Any, field: str, *, allow_zero: bool = False) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be an integer")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be an integer") from exc
    if str(value).strip() != str(parsed):
        raise ValueError(f"{field} must be an integer")
    if parsed < 0 or (parsed == 0 and not allow_zero):
        raise ValueError(f"{field} must be {'non-negative' if allow_zero else 'positive'}")
    return parsed


def _https_url(value: Any, field: str) -> str:
    url = str(value or "").strip()
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError(f"{field} must be an HTTPS URL")
    return url


def audit_realized_bitcoin_payout(
    *,
    pool_payout: dict[str, Any],
    chain_transaction: dict[str, Any],
    minimum_confirmations: int = 3,
    max_evidence_age_seconds: int = 7 * 24 * 60 * 60,
) -> dict[str, Any]:
    """Reconcile a pool payout against independently sourced on-chain transaction data.

    Required pool fields: provider, network, txid, destination, received_sats,
    status, source_url, payout_id.
    Required chain fields: network, txid, confirmations, status, outputs,
    source_url, observed_at. Each output has address and value_sats.

    This function verifies supplied evidence; it does not fetch or authenticate it.
    """
    if not isinstance(pool_payout, dict) or not isinstance(chain_transaction, dict):
        raise ValueError("pool_payout and chain_transaction must be objects")
    if isinstance(minimum_confirmations, bool) or not isinstance(minimum_confirmations, int) or minimum_confirmations < 1:
        raise ValueError("minimum_confirmations must be an integer >= 1")
    if isinstance(max_evidence_age_seconds, bool) or not isinstance(max_evidence_age_seconds, int) or max_evidence_age_seconds < 1:
        raise ValueError("max_evidence_age_seconds must be an integer >= 1")

    provider = str(pool_payout.get("provider", "")).strip()
    payout_id = str(pool_payout.get("payout_id", "")).strip()
    pool_network = str(pool_payout.get("network", "")).strip().lower()
    pool_txid = str(pool_payout.get("txid", "")).strip().lower()
    destination = str(pool_payout.get("destination", "")).strip()
    pool_status = str(pool_payout.get("status", "")).strip().lower()
    pool_source_url = _https_url(pool_payout.get("source_url"), "pool source_url")
    received_sats = _positive_int(pool_payout.get("received_sats"), "received_sats")

    chain_network = str(chain_transaction.get("network", "")).strip().lower()
    chain_txid = str(chain_transaction.get("txid", "")).strip().lower()
    chain_status = str(chain_transaction.get("status", "")).strip().upper()
    confirmations = _positive_int(
        chain_transaction.get("confirmations"), "confirmations", allow_zero=True
    )
    chain_source_url = _https_url(chain_transaction.get("source_url"), "chain source_url")
    chain_host = (urlparse(chain_source_url).hostname or "").lower()
    observed_at = str(chain_transaction.get("observed_at", "")).strip()

    if not provider or not payout_id or not destination:
        raise ValueError("provider, payout_id, and destination are required")
    if pool_network != "bitcoin" or chain_network != "bitcoin":
        raise ValueError("both evidence records must identify the bitcoin network")
    if not _TXID.fullmatch(pool_txid) or not _TXID.fullmatch(chain_txid):
        raise ValueError("txid must be a 64-character hexadecimal Bitcoin transaction ID")
    if pool_txid != chain_txid:
        raise ValueError("pool payout txid does not match independently observed chain txid")
    if pool_status not in {"confirmed", "completed", "paid"}:
        raise ValueError("pool payout must have a completed/confirmed status")
    if chain_status != "CONFIRMED":
        raise ValueError("chain transaction status must be CONFIRMED")
    if confirmations < minimum_confirmations:
        raise ValueError("insufficient blockchain confirmations")
    if chain_host not in _CHAIN_EXPLORER_HOSTS:
        raise ValueError("chain source must be a recognized public Bitcoin explorer")
    if not observed_at:
        raise ValueError("chain observed_at timestamp is required")
    try:
        normalized_timestamp = observed_at[:-1] + "+00:00" if observed_at.endswith(("Z", "z")) else observed_at
        observed_time = datetime.fromisoformat(normalized_timestamp)
    except (TypeError, ValueError) as exc:
        raise ValueError("chain observed_at must be a valid ISO 8601 timestamp") from exc
    if observed_time.tzinfo is None or observed_time.utcoffset() is None:
        raise ValueError("chain observed_at must include a timezone")
    observed_time = observed_time.astimezone(timezone.utc)
    now = datetime.now(timezone.utc)
    if observed_time > now + timedelta(minutes=5):
        raise ValueError("chain evidence timestamp is in the future")
    if now - observed_time > timedelta(seconds=max_evidence_age_seconds):
        raise ValueError("chain evidence is stale")
    if pool_source_url == chain_source_url:
        raise ValueError("pool and chain evidence must come from distinct source URLs")

    outputs = chain_transaction.get("outputs")
    if not isinstance(outputs, list) or not outputs:
        raise ValueError("chain outputs must be a non-empty list")
    destination_sats = 0
    for output in outputs:
        if not isinstance(output, dict):
            raise ValueError("each chain output must be an object")
        address = str(output.get("address", "")).strip()
        value_sats = _positive_int(output.get("value_sats"), "output value_sats", allow_zero=True)
        if address == destination:
            destination_sats += value_sats
    if destination_sats != received_sats:
        raise ValueError("pool received_sats does not match on-chain outputs to payout destination")

    return {
        "status": "MATCHED_ONCHAIN_OUTPUT_REQUIRES_TRUSTED_POOL_VERIFICATION",
        "revenue_realized": False,
        "pool_source_independently_verified": False,
        "onchain_output_amount_matched": True,
        "provider": provider,
        "payout_id": payout_id,
        "network": "bitcoin",
        "txid": pool_txid,
        "destination": destination,
        "received_sats": received_sats,
        "received_btc": f"{received_sats / 100_000_000:.8f}",
        "confirmations": confirmations,
        "pool_source_url": pool_source_url,
        "chain_source_url": chain_source_url,
        "chain_observed_at": observed_at,
        "proof_policy": {
            "pool_payout_fields_matched": True,
            "pool_source_independently_verified": False,
            "independent_chain_source_required": True,
            "destination_output_amount_matched": True,
            "minimum_confirmations": minimum_confirmations,
            "max_evidence_age_seconds": max_evidence_age_seconds,
            "evidence_freshness_verified": True,
            "network_calls_performed": False,
            "funds_moved_by_brain": False,
            "simulated_evidence_accepted": False,
        },
    }
