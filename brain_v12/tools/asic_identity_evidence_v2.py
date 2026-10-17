#!/usr/bin/env python3
"""Read-only ASIC identity evidence collector. Never authenticates hardware by itself."""
from __future__ import annotations
import argparse
import datetime as dt
import json
from pathlib import Path
import platform
import re

SERIAL_RE = re.compile(r"^[A-Za-z0-9._:/+-]{3,128}$")

def read_text(path: Path) -> str | None:
    try:
        value = path.read_text(errors="replace").strip()
        return value[:512] or None
    except OSError:
        return None

def collect_usb(root: Path = Path("/sys/bus/usb/devices")) -> list[dict]:
    devices = []
    if not root.is_dir():
        return devices
    for path in sorted(root.iterdir()):
        vendor, product = read_text(path / "idVendor"), read_text(path / "idProduct")
        if not vendor or not product:
            continue
        devices.append({
            "sysfs_path": str(path), "vendor_id": vendor, "product_id": product,
            "manufacturer": read_text(path / "manufacturer"), "product": read_text(path / "product"),
            "serial": read_text(path / "serial"), "evidence_kind": "host_usb_enumeration",
            "proves_physical_asic": False
        })
    return devices

def load_record(path: str | None) -> dict | None:
    if not path:
        return None
    try:
        record = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(record, dict):
            raise ValueError("record must be a JSON object")
        required = ("manufacturer", "model", "serial", "evidence_uri", "verified_by")
        if any(not isinstance(record.get(k), str) or not record[k].strip() for k in required):
            raise ValueError("required fields: " + ", ".join(required))
        if not SERIAL_RE.fullmatch(record["serial"].strip()):
            raise ValueError("invalid serial format")
        return {k: record[k].strip() for k in required}
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return {"record_error": str(exc)}

def build_report(usb: list[dict], record: dict | None) -> dict:
    serials = {item["serial"] for item in usb if item.get("serial")}
    valid = bool(record and not record.get("record_error"))
    match = bool(valid and record["serial"] in serials)
    return {
        "schema": "brain.asic_identity_evidence.v2",
        "captured_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "host": {"os": platform.system(), "release": platform.release(), "machine": platform.machine()},
        "collector": {"read_only": True, "network_used": False, "device_commands_sent": False},
        "status": "RECORD_SERIAL_MATCHED_REQUIRES_INDEPENDENT_REVIEW" if match else "PHYSICAL_IDENTITY_UNVERIFIED",
        "serial_match": match,
        "usb_devices": usb,
        "trusted_record": record,
        "proof_boundary": "This tool never verifies ASIC silicon or manufacturer authenticity. A serial match is only a correlation between two supplied/observed strings.",
        "required_next_evidence": [
            "Independently validate the manufacturer evidence or signed device attestation.",
            "Perform a fresh authenticated challenge-response with the actual device.",
            "Run a device-appropriate test and preserve raw device-origin output, timestamp, and identity.",
            "Keep simulator and software-node evidence classified separately from physical hardware."
        ]
    }

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trusted-record", help="JSON record independently checked by a human")
    parser.add_argument("--output", help="Write report to this path instead of stdout")
    args = parser.parse_args()
    report = build_report(collect_usb(), load_record(args.trusted_record))
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if report["status"] == "RECORD_SERIAL_MATCHED_REQUIRES_INDEPENDENT_REVIEW" else 2

if __name__ == "__main__":
    raise SystemExit(main())
