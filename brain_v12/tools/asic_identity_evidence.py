#!/usr/bin/env python3
"""Read-only, fail-closed evidence collector for physical ASIC identity.

This tool does not identify an ASIC from a model name or simulator response.
It collects host-visible USB/PCI evidence and reports PHYSICAL_IDENTITY_VERIFIED
only when an operator supplies a matching manufacturer-issued serial/attestation
and an explicit trusted-device record. No network calls, device writes, or secrets.
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys

SERIAL_RE = re.compile(r"^[A-Za-z0-9._:/+-]{3,128}$")

def read_text(path: Path) -> str | None:
    try:
        value = path.read_text(errors="replace").strip()
        return value[:512] if value else None
    except (OSError, PermissionError):
        return None

def command_output(argv: list[str]) -> tuple[str | None, str | None]:
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=4, check=False)
        return (p.stdout[:12000].strip() or None, None if p.returncode == 0 else f"exit_{p.returncode}")
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, type(exc).__name__

def collect_usb() -> list[dict]:
    rows = []
    root = Path("/sys/bus/usb/devices")
    if not root.is_dir():
        return rows
    for p in sorted(root.iterdir()):
        vendor, product = read_text(p / "idVendor"), read_text(p / "idProduct")
        if not vendor or not product:
            continue
        rows.append({
            "sysfs_path": str(p),
            "vendor_id": vendor,
            "product_id": product,
            "manufacturer": read_text(p / "manufacturer"),
            "product": read_text(p / "product"),
            "serial": read_text(p / "serial"),
            "authorized": read_text(p / "authorized"),
            "evidence_kind": "host_usb_enumeration",
            "proves_asic": False,
        })
    return rows

def load_trusted_record(path: str | None) -> dict | None:
    if not path:
        return None
    try:
        obj = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(obj, dict):
            raise ValueError("record must be a JSON object")
        required = ("manufacturer", "model", "serial", "evidence_uri", "verified_by")
        if any(not isinstance(obj.get(k), str) or not obj[k].strip() for k in required):
            raise ValueError("required non-empty fields: " + ", ".join(required))
        if not SERIAL_RE.fullmatch(obj["serial"].strip()):
            raise ValueError("serial contains unsupported characters")
        # Evidence URI is a reference for human review, not independently authenticated here.
        return {k: obj[k].strip() for k in required}
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return {"record_error": str(exc)}

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trusted-record", help="Path to an independently verified manufacturer/asset record JSON")
    parser.add_argument("--output", help="Write report to this path; default prints JSON to stdout")
    args = parser.parse_args()

    usb = collect_usb()
    lspci, lspci_error = command_output(["lspci", "-nn"])
    lsusb, lsusb_error = command_output(["lsusb", "-v"])
    record = load_trusted_record(args.trusted_record)
    serials = {d["serial"] for d in usb if d.get("serial")}
    record_valid = bool(record and not record.get("record_error"))
    serial_seen = bool(record_valid and record["serial"] in serials)
    status = "PHYSICAL_IDENTITY_VERIFIED" if record_valid and serial_seen else "PHYSICAL_IDENTITY_UNVERIFIED"
    report = {
        "schema": "brain.asic_identity_evidence.v1",
        "captured_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "host": {"os": platform.system(), "release": platform.release(), "machine": platform.machine()},
        "collector": {"read_only": True, "network_used": False, "device_commands_sent": False},
        "status": status,
        "reason": (
            "Trusted record serial matches host-enumerated USB serial; independent review of manufacturer evidence is still required."
            if serial_seen else
            "No matching trusted-record serial was observed in host USB enumeration. This is not proof that no ASIC exists."
        ),
        "usb_devices": usb,
        "pci_inventory": {"output": lspci, "error": lspci_error, "proves_asic": False},
        "usb_inventory_command": {"output": lsusb, "error": lsusb_error, "proves_asic": False},
        "trusted_record": record,
        "limitations": [
            "USB/PCI IDs, product strings, simulator APIs, and serial text alone can be spoofed and do not prove ASIC silicon.",
            "This collector does not inspect chip die identity, manufacturer signatures, firmware attestation, or mining/workload execution.",
            "PHYSICAL_IDENTITY_VERIFIED means only a supplied trusted record serial matched host USB enumeration; a human must validate the cited manufacturer evidence.",
            "No device was contacted beyond read-only host enumeration; no hardware is assumed present."
        ]
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if status == "PHYSICAL_IDENTITY_VERIFIED" else 2

if __name__ == "__main__":
    raise SystemExit(main())
