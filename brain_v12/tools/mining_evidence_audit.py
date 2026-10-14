#!/usr/bin/env python3
"""Evidence-first mining audit and profit calculator.

Offline by design: this tool never connects to hardware, a pool, a wallet, or a
blockchain. It validates evidence supplied by an authorized operator and labels
missing/weak proof as UNVERIFIED. It is not a miner.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REAL_MODES = {"PHYSICAL_DEVICE", "REMOTE_PROVIDER"}
SIMULATION_MARKERS = {"SIMULATOR", "SIMULATION", "MOCK", "SYNTHETIC", "TEST"}
REQUIRED_GATES = (
    "device_identity_attested",
    "fresh_device_telemetry",
    "pool_session_verified",
    "accepted_shares_verified",
    "payout_independently_verified",
    "costs_reconciled",
)


def parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def is_true(value: Any) -> bool:
    return value is True


def audit_record(record: dict[str, Any], *, now: datetime | None = None,
                 max_age_seconds: int = 300) -> dict[str, Any]:
    """Classify a single evidence bundle; caller assertions are not self-proving."""
    now = now or datetime.now(timezone.utc)
    mode = str(record.get("execution_mode", "")).strip().upper()
    source = str(record.get("source_type", "")).strip().upper()
    failures: list[str] = []
    checks: dict[str, bool] = {}

    simulated = mode in SIMULATION_MARKERS or source in SIMULATION_MARKERS
    checks["not_simulation"] = not simulated
    if simulated:
        failures.append("SIMULATION_IS_NOT_REAL_MINING")

    identity = record.get("device_identity")
    checks["device_identity_present"] = isinstance(identity, dict) and bool(identity.get("serial_or_provider_id"))
    checks["identity_attestation"] = is_true(record.get("device_identity_attested"))
    if not checks["device_identity_present"]:
        failures.append("DEVICE_IDENTITY_MISSING")
    if not checks["identity_attestation"]:
        failures.append("INDEPENDENT_DEVICE_ATTESTATION_MISSING")

    telemetry = record.get("telemetry")
    telemetry_time = parse_time(telemetry.get("observed_at")) if isinstance(telemetry, dict) else None
    age = (now - telemetry_time).total_seconds() if telemetry_time else None
    checks["fresh_device_telemetry"] = (
        mode in REAL_MODES and telemetry_time is not None and
        -30 <= age <= max_age_seconds and
        isinstance(telemetry, dict) and
        isinstance(telemetry.get("hashrate_hs"), (int, float)) and
        math.isfinite(float(telemetry["hashrate_hs"])) and telemetry["hashrate_hs"] > 0
    )
    if not checks["fresh_device_telemetry"]:
        failures.append("FRESH_AUTHENTICATED_DEVICE_TELEMETRY_NOT_PROVEN")

    pool = record.get("pool")
    checks["pool_session_verified"] = (
        isinstance(pool, dict) and is_true(pool.get("session_verified")) and
        bool(pool.get("pool_id")) and bool(pool.get("worker_id"))
    )
    if not checks["pool_session_verified"]:
        failures.append("LIVE_POOL_SESSION_NOT_PROVEN")

    checks["accepted_shares_verified"] = (
        isinstance(pool, dict) and is_true(pool.get("accepted_shares_independently_verified")) and
        isinstance(pool.get("accepted_shares"), int) and pool["accepted_shares"] > 0
    )
    if not checks["accepted_shares_verified"]:
        failures.append("ACCEPTED_SHARES_NOT_PROVEN")

    payout = record.get("payout")
    checks["payout_independently_verified"] = (
        isinstance(payout, dict) and is_true(payout.get("independently_verified")) and
        bool(payout.get("transaction_id")) and bool(payout.get("currency")) and
        isinstance(payout.get("amount"), (int, float)) and payout["amount"] > 0
    )
    if not checks["payout_independently_verified"]:
        failures.append("INDEPENDENT_PAYOUT_PROOF_MISSING")

    costs = record.get("costs")
    checks["costs_reconciled"] = (
        isinstance(costs, dict) and
        all(isinstance(costs.get(k), (int, float)) and math.isfinite(float(costs[k])) and costs[k] >= 0
            for k in ("electricity", "pool_fees", "hosting", "other"))
    )
    if not checks["costs_reconciled"]:
        failures.append("COST_LEDGER_INCOMPLETE")

    # Claims in JSON cannot attest themselves. Require an evidence reference for each
    # critical proof and a digest of the exact input document for reproducibility.
    evidence = record.get("evidence_refs")
    checks["evidence_references_present"] = isinstance(evidence, dict) and all(
        bool(evidence.get(k)) for k in REQUIRED_GATES
    )
    if not checks["evidence_references_present"]:
        failures.append("EVIDENCE_REFERENCES_INCOMPLETE")

    gates_passed = all(checks.get(g, False) for g in (
        "not_simulation", "device_identity_present", "identity_attestation",
        "fresh_device_telemetry", "pool_session_verified",
        "accepted_shares_verified", "payout_independently_verified", "costs_reconciled",
        "evidence_references_present",
    ))
    return {
        "schema": "brain.mining-evidence-audit.v1",
        "status": "EVIDENCE_COMPLETE_REQUIRES_HUMAN_REVIEW" if gates_passed else "UNVERIFIED",
        "real_mining_proven": gates_passed,
        "checks": checks,
        "failures": failures,
        "telemetry_age_seconds": round(age, 3) if age is not None else None,
        "input_record_sha256": hashlib.sha256(
            json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "note": "Evidence references and supplied booleans require independent source review; this offline tool does not establish network/device truth.",
    }


def calculate_profit(ledger: dict[str, Any]) -> dict[str, Any]:
    """Calculate realized net only from explicitly verified receipts and recorded costs."""
    currency = str(ledger.get("currency", "")).strip().upper()
    if not currency:
        raise ValueError("CURRENCY_REQUIRED")
    payouts = ledger.get("verified_payouts", [])
    costs = ledger.get("costs", {})
    if not isinstance(payouts, list) or not isinstance(costs, dict):
        raise ValueError("INVALID_LEDGER_SHAPE")

    realized = 0.0
    payout_ids: set[str] = set()
    for item in payouts:
        if not isinstance(item, dict) or item.get("currency", "").upper() != currency:
            raise ValueError("PAYOUT_CURRENCY_MISMATCH_OR_INVALID_ENTRY")
        if item.get("independently_verified") is not True:
            raise ValueError("UNVERIFIED_PAYOUT_CANNOT_COUNT_AS_REALIZED_REVENUE")
        txid = str(item.get("transaction_id", "")).strip()
        amount = item.get("amount")
        if not txid or txid in payout_ids:
            raise ValueError("MISSING_OR_DUPLICATE_PAYOUT_TRANSACTION_ID")
        if not isinstance(amount, (int, float)) or not math.isfinite(float(amount)) or amount < 0:
            raise ValueError("INVALID_PAYOUT_AMOUNT")
        payout_ids.add(txid)
        realized += float(amount)

    cost_keys = ("electricity", "pool_fees", "hosting", "hardware_amortization", "other")
    normalized_costs: dict[str, float] = {}
    for key in cost_keys:
        value = costs.get(key, 0)
        if not isinstance(value, (int, float)) or not math.isfinite(float(value)) or value < 0:
            raise ValueError("INVALID_COST_" + key.upper())
        normalized_costs[key] = float(value)

    total_cost = sum(normalized_costs.values())
    return {
        "schema": "brain.mining-profit-ledger.v1",
        "currency": currency,
        "verified_realized_revenue": round(realized, 12),
        "costs": normalized_costs,
        "total_costs": round(total_cost, 12),
        "realized_net_profit": round(realized - total_cost, 12),
        "payout_count": len(payout_ids),
        "status": "CALCULATED_FROM_VERIFIED_INPUTS" if payouts else "NO_VERIFIED_REVENUE",
        "note": "This arithmetic does not independently verify transactions or costs; retain provenance for every entry.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("audit", "profit"))
    parser.add_argument("input", type=Path, help="JSON input file")
    parser.add_argument("--output", type=Path, help="Optional output JSON path")
    args = parser.parse_args()
    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("TOP_LEVEL_JSON_MUST_BE_OBJECT")
        result = audit_record(data) if args.mode == "audit" else calculate_profit(data)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        parser.error(str(exc))
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
