"""Fail-closed evidence gate for hosted physical ASIC claims.

This module does not discover hardware, contact a pool, provision resources,
or verify external evidence. It classifies supplied evidence for the next
independent verification step; it must never label a claim as verified.
"""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse


def _https_url(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value.strip())
    return parsed.scheme == "https" and bool(parsed.netloc)


def assess_asic_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    """Return the strongest evidence stage supported by fields supplied.

    Field presence is not proof that a device, hashrate, or payout is real.
    """
    errors: list[str] = []
    required_identity = {
        "provider_legal_name": "PROVIDER_IDENTITY_MISSING",
        "device_model": "DEVICE_MODEL_MISSING",
        "device_serial_or_provider_asset_id": "DEVICE_IDENTITY_MISSING",
        "facility_evidence_url": "FACILITY_EVIDENCE_MISSING",
    }
    for key, error in required_identity.items():
        value = evidence.get(key)
        if not isinstance(value, str) or not value.strip():
            errors.append(error)

    if evidence.get("physical_asic_confirmed") is not True:
        errors.append("PHYSICAL_ASIC_NOT_CONFIRMED")
    if not _https_url(evidence.get("facility_evidence_url")):
        errors.append("FACILITY_EVIDENCE_URL_INVALID")

    if errors:
        stage = "BLOCKED"
    else:
        stage = "DEVICE_CLAIM_REQUIRES_INDEPENDENT_VERIFICATION"

    pool_url = evidence.get("pool_dashboard_url")
    try:
        hashrate = float(evidence.get("observed_hashrate_ths", 0))
    except (TypeError, ValueError):
        hashrate = 0
    try:
        accepted_shares = int(evidence.get("accepted_shares", 0))
    except (TypeError, ValueError):
        accepted_shares = 0

    if stage != "BLOCKED":
        if not _https_url(pool_url):
            errors.append("POOL_EVIDENCE_URL_INVALID")
        if hashrate <= 0:
            errors.append("POSITIVE_OBSERVED_HASHRATE_MISSING")
        if accepted_shares <= 0:
            errors.append("ACCEPTED_POOL_SHARES_MISSING")
        if not errors:
            stage = "MINING_CLAIM_REQUIRES_INDEPENDENT_VERIFICATION"

    payout_txid = evidence.get("payout_transaction_id")
    try:
        payout_btc = float(evidence.get("payout_amount_btc", 0))
    except (TypeError, ValueError):
        payout_btc = 0
    if stage == "MINING_CLAIM_REQUIRES_INDEPENDENT_VERIFICATION":
        if not isinstance(payout_txid, str) or not payout_txid.strip() or payout_btc <= 0:
            errors.append("MATCHABLE_PAYOUT_EVIDENCE_MISSING")
        else:
            stage = "PAYOUT_CLAIM_REQUIRES_INDEPENDENT_VERIFICATION"

    return {
        "schema_version": 1,
        "component": "Brain ASIC Evidence Gate",
        "stage": stage,
        "claim_verified": False,
        "automatic_activation_allowed": False,
        "evidence_errors": sorted(set(errors)),
        "next_required_action": (
            "Obtain a verifiable provider/device identity and facility evidence."
            if stage == "BLOCKED" else
            "Independently verify device identity, live pool telemetry, and payout evidence; do not infer verification from field presence."
        ),
        "safety": {
            "network_contacted": False,
            "resources_created": False,
            "payments_made": False,
            "mining_started": False,
            "wallet_secrets_requested": False,
        },
    }
