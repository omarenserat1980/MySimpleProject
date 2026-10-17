"""Evidence-first identity registry for BRAIN-ASIC-001.

The Brain product ID is a logical project identifier, not a chip serial number.
This module normalizes operator-supplied or read-only-discovered metadata. It
never scans networks, starts mining, or treats unverified claims as evidence.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PRODUCT_ID = "BRAIN-ASIC-001"
OUTPUT_DEFAULT = Path("artifacts/asic-unit-001/identity-record.json")
HEX_ID = re.compile(r"^(?:0x)?[0-9a-fA-F]{4,8}$")


def normalize_identity(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize known fields; verification requires linked evidence references."""
    if not isinstance(raw, dict):
        raise ValueError("identity input must be a JSON object")
    connection = {
        "transport": raw.get("transport") or None,
        "usb_vid": raw.get("usb_vid") or None,
        "usb_pid": raw.get("usb_pid") or None,
        "usb_serial": raw.get("usb_serial") or None,
        "interface": raw.get("interface") or None,
        "host": raw.get("host") or None,
        "port": raw.get("port") or None,
        "device_path": raw.get("device_path") or None,
    }
    for field in ("usb_vid", "usb_pid"):
        value = connection[field]
        if value is not None and not HEX_ID.fullmatch(str(value)):
            raise ValueError(f"{field} must be a 4-8 digit hexadecimal ID, e.g. 1d6b")
        if value is not None:
            connection[field] = str(value).lower().removeprefix("0x").zfill(4)

    evidence = {
        "datasheet_url": raw.get("datasheet_url") or None,
        "vendor_product_url": raw.get("vendor_product_url") or None,
        "photo_or_label_evidence": raw.get("photo_or_label_evidence") or None,
        "discovery_method": raw.get("discovery_method") or "operator_supplied",
        "device_identity_evidence": raw.get("device_identity_evidence") or None,
        "connection_test_evidence": raw.get("connection_test_evidence") or None,
        "accepted_share_evidence": raw.get("accepted_share_evidence") or None,
        "evidence_file": raw.get("evidence_file") or None,
    }
    identity = {
        "schema": "brain-asic-identity/v1",
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "brain_product_id": PRODUCT_ID,
        "component_ids": {
            "compute_device": "BRAIN-ASIC-001-U1",
            "board": "BRAIN-ASIC-001-PCB1",
        },
        "manufacturer": raw.get("manufacturer") or None,
        "device_model": raw.get("device_model") or None,
        "chip_part_number": raw.get("chip_part_number") or None,
        "board_model": raw.get("board_model") or None,
        "board_revision": raw.get("board_revision") or None,
        "manufacturer_serial_number": raw.get("manufacturer_serial_number") or None,
        "brain_asset_tag": raw.get("brain_asset_tag") or PRODUCT_ID,
        "lot_or_batch": raw.get("lot_or_batch") or None,
        "connection": connection,
        "evidence": evidence,
        "verification_claims": {
            "physical_device_seen": raw.get("physical_device_seen") is True,
            "manufacturer_identity_verified": raw.get("manufacturer_identity_verified") is True,
            "serial_number_verified": raw.get("serial_number_verified") is True,
            "connection_tested": raw.get("connection_tested") is True,
            "pool_accepted_share_verified": raw.get("pool_accepted_share_verified") is True,
        },
    }
    required = (
        identity["manufacturer"],
        identity["device_model"],
        identity["chip_part_number"] or identity["board_model"],
        identity["manufacturer_serial_number"] or connection["usb_serial"],
        evidence["datasheet_url"] or evidence["vendor_product_url"],
    )
    identity["identity_complete"] = all(required)
    claims = identity["verification_claims"]
    identity["physical_hardware_verified"] = (
        identity["identity_complete"]
        and claims["physical_device_seen"]
        and claims["manufacturer_identity_verified"]
        and claims["serial_number_verified"]
        and bool(evidence["device_identity_evidence"])
        and bool(evidence["photo_or_label_evidence"] or evidence["evidence_file"])
    )
    identity["connection_verified"] = (
        identity["physical_hardware_verified"]
        and claims["connection_tested"]
        and bool(evidence["connection_test_evidence"])
    )
    identity["mining_live_verified"] = (
        identity["connection_verified"]
        and claims["pool_accepted_share_verified"]
        and bool(evidence["accepted_share_evidence"])
    )
    identity["status"] = (
        "LIVE_MINING_EVIDENCE_VERIFIED" if identity["mining_live_verified"]
        else "CONNECTION_EVIDENCE_VERIFIED" if identity["connection_verified"]
        else "PHYSICAL_DEVICE_IDENTITY_VERIFIED" if identity["physical_hardware_verified"]
        else "IDENTIFICATION_INCOMPLETE"
    )
    identity["safety_note"] = (
        "BRAIN-ASIC-001 is a Brain asset label, not proof of a manufactured chip. "
        "A boolean claim alone is not evidence; verification requires evidence references. "
        "Never infer model, serial, hashrate, or mining activity from this label."
    )
    return identity


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate BRAIN-ASIC-001 identity metadata")
    parser.add_argument("--input", type=Path, help="JSON file with known identity fields")
    parser.add_argument("--output", type=Path, default=OUTPUT_DEFAULT)
    parser.add_argument("--stdout", action="store_true")
    args = parser.parse_args()
    raw = json.loads(args.input.read_text(encoding="utf-8")) if args.input else {}
    if not isinstance(raw, dict):
        parser.error("input JSON must be an object")
    record = normalize_identity(raw)
    serialized = json.dumps(record, indent=2, ensure_ascii=False) + "\n"
    if args.stdout:
        print(serialized, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
        print(f"wrote {args.output}; status={record['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
