#!/usr/bin/env python3
"""Fail-closed preflight for a zero-budget hosted Bitcoin ASIC offer.

This tool validates a provider-supplied offer document. It does not contact a
provider, provision compute, mine Bitcoin, move funds, or verify external claims.
A PASS means only that the offer has enough fields for manual review.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def assess(offer: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = [
        "Provider claims and URLs are not independently verified by this tool.",
        "No ASIC is provisioned and no mining/payout is started by this preflight.",
    ]

    def required_text(key: str) -> str:
        value = offer.get(key)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"MISSING_{key.upper()}")
            return ""
        return value.strip()

    operator = required_text("operator_legal_name")
    facility = required_text("facility_evidence_url")
    pool = required_text("public_pool_or_payout_evidence_url")
    trial_terms = required_text("trial_terms_url")

    try:
        hashrate = float(offer.get("trial_hashrate_ths", 0))
        if not math.isfinite(hashrate) or hashrate <= 0:
            errors.append("INVALID_TRIAL_HASHRATE_THS")
    except (TypeError, ValueError):
        hashrate = 0
        errors.append("INVALID_TRIAL_HASHRATE_THS")

    # A zero-budget offer must not require an upfront payment, deposit,
    # recurring charge, paid upgrade, referral unlock, or withdrawal fee.
    for key in ("upfront_cost_usd", "deposit_required_usd", "recurring_cost_usd",
                "withdrawal_fee_usd", "activation_fee_usd"):
        try:
            value = float(offer.get(key, -1))
            if not math.isfinite(value) or value < 0:
                errors.append(f"INVALID_{key.upper()}")
            elif value != 0:
                errors.append(f"NONZERO_{key.upper()}")
        except (TypeError, ValueError):
            errors.append(f"INVALID_{key.upper()}")

    if offer.get("trial_rewards_withdrawable") is not True:
        errors.append("TRIAL_REWARDS_NOT_CONFIRMED_WITHDRAWABLE")
    if offer.get("requires_paid_upgrade_to_withdraw") is not False:
        errors.append("PAID_UPGRADE_WITHDRAWAL_RISK")
    if offer.get("requires_referrals_to_withdraw") is not False:
        errors.append("REFERRAL_WITHDRAWAL_RISK")
    if offer.get("requires_wallet_seed_or_private_key") is not False:
        errors.append("WALLET_SECRET_REQUEST_RISK")
    if offer.get("physical_asic_disclosed") is not True:
        errors.append("PHYSICAL_ASIC_NOT_CONFIRMED")
    if offer.get("external_wallet_payout_supported") is not True:
        errors.append("EXTERNAL_WALLET_PAYOUT_NOT_CONFIRMED")

    # Presence of a URL is not proof that a provider, facility, or payout is real.
    if facility and not facility.startswith("https://"):
        errors.append("FACILITY_EVIDENCE_URL_MUST_USE_HTTPS")
    if pool and not pool.startswith("https://"):
        errors.append("POOL_OR_PAYOUT_EVIDENCE_URL_MUST_USE_HTTPS")
    if trial_terms and not trial_terms.startswith("https://"):
        errors.append("TRIAL_TERMS_URL_MUST_USE_HTTPS")

    return {
        "schema_version": 1,
        "component": "Brain ASIC Hosting Preflight",
        "budget_usd": 0,
        "status": "NEEDS_MANUAL_REVIEW" if not errors else "BLOCKED",
        "eligible_for_automatic_activation": False,
        "provider_operator": operator or None,
        "trial_hashrate_ths": hashrate or None,
        "errors": sorted(set(errors)),
        "warnings": warnings,
        "safety": {
            "network_contacted": False,
            "cloud_resources_created": False,
            "payments_made": False,
            "wallet_secrets_requested": False,
            "mining_started": False,
            "withdrawal_verified": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offer", required=True, help="Path to a provider offer JSON file")
    parser.add_argument("--output", default="brain-asic-hosting-preflight.json")
    args = parser.parse_args()

    try:
        offer = json.loads(Path(args.offer).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc)}, indent=2))
        return 2
    if not isinstance(offer, dict):
        print(json.dumps({"status": "BLOCKED", "error": "OFFER_MUST_BE_JSON_OBJECT"}, indent=2))
        return 2

    report = assess(offer)
    Path(args.output).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "NEEDS_MANUAL_REVIEW" else 1


if __name__ == "__main__":
    raise SystemExit(main())
