#!/usr/bin/env python3
"""Fail-closed preflight for zero-budget hosted ASIC trial offers.

This tool validates only the structure and declared terms of an offer. It does
not verify a provider, make network requests, start mining, or authorize payment.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


REQUIRED_URLS = (
    "facility_evidence_url",
    "public_pool_or_payout_evidence_url",
    "trial_terms_url",
)
ZERO_COST_FIELDS = (
    "upfront_cost_usd",
    "deposit_required_usd",
    "recurring_cost_usd",
    "withdrawal_fee_usd",
    "activation_fee_usd",
)
REQUIRED_FIELDS = (
    "operator_legal_name",
    *REQUIRED_URLS,
    "trial_hashrate_ths",
    *ZERO_COST_FIELDS,
    "trial_rewards_withdrawable",
    "requires_paid_upgrade_to_withdraw",
    "requires_referrals_to_withdraw",
    "requires_wallet_seed_or_private_key",
    "physical_asic_disclosed",
    "external_wallet_payout_supported",
)


def _is_true(value: Any) -> bool:
    return value is True


def _is_false(value: Any) -> bool:
    return value is False


def assess(offer: dict[str, Any]) -> dict[str, Any]:
    """Assess declared terms; missing, malformed, or unsafe fields fail closed."""
    errors: list[str] = []

    if not isinstance(offer, dict):
        offer = {}
        errors.append("OFFER_MUST_BE_OBJECT")

    for field in REQUIRED_FIELDS:
        if field not in offer:
            errors.append(f"MISSING_REQUIRED_FIELD:{field}")

    if not isinstance(offer.get("operator_legal_name"), str) or not offer.get("operator_legal_name", "").strip():
        if "MISSING_REQUIRED_FIELD:operator_legal_name" not in errors:
            errors.append("OPERATOR_LEGAL_NAME_MISSING")

    for field in REQUIRED_URLS:
        value = offer.get(field)
        try:
            parsed = urlparse(value) if isinstance(value, str) else None
            valid = parsed is not None and parsed.scheme == "https" and bool(parsed.netloc)
        except ValueError:
            valid = False
        if field in offer and not valid:
            errors.append(f"INVALID_HTTPS_URL:{field}")

    hashrate = offer.get("trial_hashrate_ths")
    if "trial_hashrate_ths" in offer:
        if isinstance(hashrate, bool) or not isinstance(hashrate, (int, float)) or not math.isfinite(hashrate) or hashrate <= 0:
            errors.append("INVALID_TRIAL_HASHRATE_THS")

    for field in ZERO_COST_FIELDS:
        if field not in offer:
            continue
        value = offer[field]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            errors.append(f"INVALID_COST_USD:{field}")
        elif value != 0:
            errors.append(f"NONZERO_{field.upper()}")

    boolean_rules = (
        ("trial_rewards_withdrawable", _is_true, "TRIAL_REWARDS_NOT_CONFIRMED_WITHDRAWABLE"),
        ("requires_paid_upgrade_to_withdraw", _is_false, "PAID_UPGRADE_REQUIRED_TO_WITHDRAW"),
        ("requires_referrals_to_withdraw", _is_false, "REFERRALS_REQUIRED_TO_WITHDRAW"),
        ("requires_wallet_seed_or_private_key", _is_false, "WALLET_SECRET_REQUEST_RISK"),
        ("physical_asic_disclosed", _is_true, "PHYSICAL_ASIC_NOT_CONFIRMED"),
        ("external_wallet_payout_supported", _is_true, "EXTERNAL_WALLET_PAYOUT_NOT_SUPPORTED"),
    )
    for field, predicate, error_code in boolean_rules:
        if field in offer and not predicate(offer[field]):
            errors.append(error_code)

    # Stable, deterministic evidence shape; structural eligibility is not trust.
    errors = list(dict.fromkeys(errors))
    status = "BLOCKED" if errors else "NEEDS_MANUAL_REVIEW"
    return {
        "status": status,
        "errors": errors,
        "eligible_for_automatic_activation": False,
        "safety": {
            "mining_started": False,
            "withdrawal_verified": False,
            "provider_identity_verified": False,
            "payment_authorized": False,
        },
        "disclaimer": (
            "Structural preflight only. Provider legitimacy, published terms, "
            "hashrate, and payout claims are not independently verified."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offer", required=True, help="Path to offer JSON")
    parser.add_argument("--output", required=True, help="Path for JSON assessment")
    args = parser.parse_args()

    try:
        offer = json.loads(Path(args.offer).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        result = {
            "status": "BLOCKED",
            "errors": [f"OFFER_READ_FAILED:{type(exc).__name__}"],
            "eligible_for_automatic_activation": False,
            "safety": {
                "mining_started": False,
                "withdrawal_verified": False,
                "provider_identity_verified": False,
                "payment_authorized": False,
            },
        }
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2))
        return 2

    result = assess(offer)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "NEEDS_MANUAL_REVIEW" else 2


if __name__ == "__main__":
    raise SystemExit(main())
