#!/usr/bin/env python3
"""Fail-closed gate for evidence of an actual FPGA/ASIC device.

This validates an evidence bundle's structure and hashes; it cannot independently
authenticate a foundry, serial number, photograph, or claimed physical device.
No evidence bundle means BLOCKED, never VERIFIED.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

REQUIRED_COMMON = (
    "device_type", "manufacturer", "part_number", "serial_number",
    "connection_interface", "probe_command", "probe_exit_code",
    "probe_output_file", "probe_output_sha256", "captured_at_utc",
    "independent_evidence",
)
REQUIRED_ASIC = (
    "foundry", "wafer_lot", "die_id", "package_id",
    "manufacturing_or_test_report",
)
REQUIRED_BRINGUP = (
    "test_id", "input_vector", "expected_output", "observed_output",
    "device_identity", "captured_at_utc", "raw_log_file", "raw_log_sha256",
)

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            h.update(block)
    return h.hexdigest()

def nonempty(value) -> bool:
    return isinstance(value, str) and bool(value.strip())

def utc_timestamp(value) -> bool:
    if not isinstance(value, str) or not value.endswith("Z"):
        return False
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
        return True
    except ValueError:
        return False

def evaluate(root: Path) -> dict:
    issues = []
    device_path = root / "device_attestation.json"
    bringup_path = root / "bringup_test.json"
    if not device_path.is_file() or not bringup_path.is_file():
        return {
            "schema_version": 1,
            "status": "BLOCKED_PHYSICAL_EVIDENCE_MISSING",
            "physical_hardware_verified": False,
            "evidence_directory": str(root),
            "missing_files": [str(p.name) for p in (device_path, bringup_path) if not p.is_file()],
            "issues": ["No physical device is proven by RTL simulation or software tests."],
        }
    try:
        device = json.loads(device_path.read_text(encoding="utf-8"))
        bringup = json.loads(bringup_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"schema_version": 1, "status": "REJECTED_INVALID_EVIDENCE", "physical_hardware_verified": False, "issues": [type(exc).__name__]}

    if not isinstance(device, dict) or not isinstance(bringup, dict):
        return {"schema_version": 1, "status": "REJECTED_INVALID_EVIDENCE", "physical_hardware_verified": False, "issues": ["Evidence documents must be JSON objects."]}

    for field in REQUIRED_COMMON:
        if field not in device or device[field] is None or device[field] == "":
            issues.append("DEVICE_FIELD_MISSING:" + field)
    for field in REQUIRED_BRINGUP:
        if field not in bringup or bringup[field] is None or bringup[field] == "":
            issues.append("BRINGUP_FIELD_MISSING:" + field)

    kind = str(device.get("device_type", "")).upper()
    if kind not in {"ASIC", "FPGA"}:
        issues.append("DEVICE_TYPE_MUST_BE_ASIC_OR_FPGA")
    if kind == "ASIC":
        for field in REQUIRED_ASIC:
            if not nonempty(device.get(field)):
                issues.append("ASIC_FABRICATION_FIELD_MISSING:" + field)
    if device.get("probe_exit_code") != 0:
        issues.append("PHYSICAL_DEVICE_PROBE_NOT_SUCCESSFUL")
    if not utc_timestamp(device.get("captured_at_utc")):
        issues.append("DEVICE_CAPTURE_TIME_MUST_BE_UTC_ISO8601")
    if not utc_timestamp(bringup.get("captured_at_utc")):
        issues.append("BRINGUP_CAPTURE_TIME_MUST_BE_UTC_ISO8601")
    if bringup.get("device_identity") != device.get("serial_number"):
        issues.append("BRINGUP_DEVICE_IDENTITY_MISMATCH")

    probe_file = root / str(device.get("probe_output_file", ""))
    if not probe_file.is_file():
        issues.append("RAW_DEVICE_PROBE_LOG_MISSING")
    elif sha256(probe_file) != device.get("probe_output_sha256"):
        issues.append("RAW_DEVICE_PROBE_HASH_MISMATCH")

    raw_log = root / str(bringup.get("raw_log_file", ""))
    if not raw_log.is_file():
        issues.append("RAW_BRINGUP_LOG_MISSING")
    elif sha256(raw_log) != bringup.get("raw_log_sha256"):
        issues.append("RAW_BRINGUP_LOG_HASH_MISMATCH")

    independent = device.get("independent_evidence")
    if not isinstance(independent, list) or len(independent) < 1 or not all(nonempty(x) for x in independent):
        issues.append("INDEPENDENT_EVIDENCE_REFERENCE_REQUIRED")

    if bringup.get("expected_output") != bringup.get("observed_output"):
        issues.append("PHYSICAL_BRINGUP_OUTPUT_MISMATCH")

    return {
        "schema_version": 1,
        "status": "EVIDENCE_BUNDLE_STRUCTURALLY_VALID_REQUIRES_INDEPENDENT_REVIEW" if not issues else "REJECTED_OR_INCOMPLETE",
        "physical_hardware_verified": False,
        "device_type": kind or None,
        "serial_number": device.get("serial_number"),
        "evidence_directory": str(root),
        "issues": issues,
        "warning": "Hash and schema checks do not authenticate physical existence. Independent review of device, manufacturing provenance, and live bring-up evidence is mandatory.",
    }

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", default="artifacts/asic/physical-evidence")
    args = parser.parse_args()
    result = evaluate(Path(args.evidence_dir))
    print(json.dumps(result, indent=2, sort_keys=True))
    # This tool never grants VERIFIED status by itself.
    return 0 if result["status"] == "EVIDENCE_BUNDLE_STRUCTURALLY_VALID_REQUIRES_INDEPENDENT_REVIEW" else 2

if __name__ == "__main__":
    raise SystemExit(main())
