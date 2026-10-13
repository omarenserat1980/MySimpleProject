#!/usr/bin/env python3
"""Fail-closed evidence gate for distinguishing ASIC simulation from physical hardware.

This tool validates a signed evidence envelope; it does not discover hardware or
create trust by itself. The HMAC key must be provisioned out-of-band by the
operator and must never be committed to the repository. A PASS means the supplied
bundle passed this gate, not that an independent physical inspection occurred.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REQUIRED_EVIDENCE = {
    "schema_version", "evidence_type", "device_id", "device_model",
    "transport", "challenge_nonce", "device_response", "test_name",
    "test_result", "observed_at", "raw_evidence_sha256", "verifier_id",
}
ALLOWED_TRANSPORTS = {"usb", "serial", "ethernet", "pcie", "i2c", "spi", "jtag", "vendor_api"}


def canonical_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def parse_time(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError("observed_at must be an ISO-8601 string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("observed_at must include a timezone")
    return parsed.astimezone(timezone.utc)


def validate_bundle(bundle: Any, key: bytes | None) -> dict[str, Any]:
    failures: list[str] = []
    if not isinstance(bundle, dict):
        return {"status": "BLOCKED", "classification": "UNVERIFIED", "failures": ["top-level JSON must be an object"]}
    payload = bundle.get("payload")
    signature = bundle.get("hmac_sha256")
    if not isinstance(payload, dict):
        return {"status": "BLOCKED", "classification": "UNVERIFIED", "failures": ["payload object is missing"]}

    missing = sorted(REQUIRED_EVIDENCE - payload.keys())
    if missing:
        failures.append("missing required fields: " + ", ".join(missing))
    if payload.get("schema_version") != "1.0":
        failures.append("unsupported schema_version; expected 1.0")
    if payload.get("evidence_type") != "physical_asic":
        failures.append("evidence_type must be physical_asic; simulation is not physical hardware")
    for field in ("device_id", "device_model", "challenge_nonce", "device_response", "test_name", "verifier_id"):
        if not isinstance(payload.get(field), str) or not payload.get(field, "").strip():
            failures.append(field + " must be a non-empty string")
    if payload.get("transport") not in ALLOWED_TRANSPORTS:
        failures.append("transport must identify a supported physical transport")
    if payload.get("test_result") != "PASS":
        failures.append("physical-device test_result is not PASS")
    digest = payload.get("raw_evidence_sha256")
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest.lower()):
        failures.append("raw_evidence_sha256 must be a 64-character SHA-256 hex digest")
    try:
        observed = parse_time(payload.get("observed_at"))
        now = datetime.now(timezone.utc)
        if observed > now:
            failures.append("observed_at is in the future")
        if (now - observed).total_seconds() > 86400:
            failures.append("evidence is older than 24 hours; capture a fresh device challenge")
    except (TypeError, ValueError, OverflowError):
        failures.append("observed_at must be valid timezone-aware ISO-8601")

    signature_ok = False
    if key is None:
        failures.append("BRAIN_ASIC_EVIDENCE_HMAC_KEY is not configured out-of-band")
    elif not isinstance(signature, str) or not signature:
        failures.append("hmac_sha256 signature is missing")
    else:
        expected = hmac.new(key, canonical_bytes(payload), hashlib.sha256).hexdigest()
        signature_ok = hmac.compare_digest(expected, signature.lower())
        if not signature_ok:
            failures.append("evidence signature verification failed")

    passed = not failures and signature_ok
    return {
        "status": "PASS" if passed else "BLOCKED",
        "classification": "PHYSICAL_ASIC_EVIDENCE_BUNDLE_VERIFIED" if passed else "UNVERIFIED_NOT_PROVEN_HARDWARE",
        "device_id": payload.get("device_id"),
        "device_model": payload.get("device_model"),
        "transport": payload.get("transport"),
        "test_name": payload.get("test_name"),
        "test_result": payload.get("test_result"),
        "signature_verified": signature_ok,
        "failures": failures,
        "limitations": [
            "This verifies the supplied envelope against a locally configured HMAC key; it does not independently inspect the device.",
            "Trust depends on secure out-of-band key provisioning and on the verifier that generated the signed evidence.",
            "A passing bundle is not proof of manufacturing provenance unless the verifier and identity source are independently trusted.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence_json", help="Path to a signed JSON evidence envelope")
    args = parser.parse_args()
    try:
        bundle = json.loads(Path(args.evidence_json).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "BLOCKED", "classification": "UNVERIFIED", "failures": [f"cannot read evidence JSON: {type(exc).__name__}"]}, indent=2))
        return 2
    secret = os.environ.get("BRAIN_ASIC_EVIDENCE_HMAC_KEY")
    key = secret.encode("utf-8") if secret else None
    result = validate_bundle(bundle, key)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
