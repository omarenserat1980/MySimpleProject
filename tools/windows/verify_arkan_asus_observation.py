#!/usr/bin/env python3
"""Fail-closed verifier for an Arkan ASUS Golden Loop observation report.

This verifies report integrity and freshness only. It does NOT prove the report
came from the physical ASUS; a human must inspect hostname/model and context.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("report", nargs="?", default="arkan-asus-golden-observation.json")
    parser.add_argument("--max-age-hours", type=float, default=24.0)
    args = parser.parse_args()

    path = Path(args.report)
    try:
        result = json.loads(path.read_text(encoding="utf-8-sig"))
        canonical = result["payload_canonical_json"]
        expected_hash = result["payload_sha256"]
        payload = result["payload"]
        if not isinstance(canonical, str) or not isinstance(expected_hash, str):
            raise ValueError("canonical JSON or SHA-256 has wrong type")
        actual_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        if actual_hash.lower() != expected_hash.lower():
            raise ValueError(f"SHA-256 mismatch: expected {expected_hash}, computed {actual_hash}")
        decoded = json.loads(canonical)
        if decoded != payload:
            raise ValueError("payload differs from payload_canonical_json")
        if payload.get("schema") != "brain.arkan-asus-golden-loop-observation.v1":
            raise ValueError("unexpected schema")
        if payload.get("mission") != "ARKAN_ASUS_COMPUTER_BUILD":
            raise ValueError("unexpected mission")
        if payload.get("stage") != "OBSERVE":
            raise ValueError("report is not an OBSERVE-stage report")
        timestamp = datetime.fromisoformat(payload["observed_at_utc"].replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            raise ValueError("observation timestamp has no timezone")
        age_hours = (datetime.now(timezone.utc) - timestamp.astimezone(timezone.utc)).total_seconds() / 3600
        if age_hours < -0.1:
            raise ValueError("observation timestamp is in the future")
        if age_hours > args.max_age_hours:
            raise ValueError(f"stale report: {age_hours:.2f} hours old")
        host = payload.get("host") or {}
        if not host.get("computer_name") or not host.get("manufacturer") or not host.get("model"):
            raise ValueError("host identity fields are incomplete")
        print("REPORT_INTEGRITY=PASS")
        print(f"SHA256={actual_hash}")
        print(f"OBSERVED_AT_UTC={timestamp.astimezone(timezone.utc).isoformat()}")
        print(f"AGE_HOURS={age_hours:.2f}")
        print(f"HOSTNAME={host['computer_name']}")
        print(f"MANUFACTURER_MODEL={host['manufacturer']} {host['model']}")
        print("PHYSICAL_ASUS_IDENTITY=MANUAL_REVIEW_REQUIRED")
        print("MISSION_STATE=OPEN_NOT_CLOSED")
        print("This verifier does not authorize VM start, system changes, or cloud spending.")
        return 0
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"REPORT_INTEGRITY=FAIL: {exc}", file=sys.stderr)
        print("MISSION_STATE=OPEN_NOT_CLOSED", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
