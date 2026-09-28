#!/usr/bin/env python3
"""Honda CONNECT firmware intake and compatibility brain.

The vehicle-side export is expected to be a JSON file such as
HondaSoftwareUpdates/rb/update_by_usb.json or update_by_usb.json.

The brain extracts version/package metadata and only selects an app package
when an explicit compatibility rule and verified source are present.
It never invents a firmware package or performs vehicle installation.
"""

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "apps.json"


def version_tuple(value):
    nums = re.findall(r"\d+", value or "")
    return tuple(int(x) for x in nums[:4]) if nums else ()


def compatible(app, firmware):
    rules = app.get("compatibility_rules", [])
    if not rules:
        return None, "no compatibility rule"

    fv = version_tuple(firmware)
    if not fv:
        return None, "firmware version not parseable"

    for rule in rules:
        if rule.get("exact") and firmware.strip() == rule["exact"].strip():
            return True, "exact firmware match"

        min_v = version_tuple(rule.get("min", ""))
        max_v = version_tuple(rule.get("max", ""))
        if min_v and fv < min_v:
            continue
        if max_v and fv > max_v:
            continue
        return True, "firmware is inside supported range"

    return False, "firmware outside supported ranges"


def load_vehicle_export(path):
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))

    def first(*keys):
        for key in keys:
            value = data.get(key)
            if value not in (None, ""):
                return str(value)
        return ""

    firmware = first(
        "softwareVersion", "software_version", "systemVersion",
        "system_version", "version", "firmwareVersion", "firmware_version"
    )
    package = first("package", "packageName", "package_name", "fileName", "filename")
    sha256 = first("sha256", "SHA256", "packageSha256", "package_sha256")

    return {
        "source_file": str(p),
        "system_version": first("systemVersion", "system_version"),
        "software_version": first("softwareVersion", "software_version"),
        "hardware_version": first("hardwareVersion", "hardware_version"),
        "mcu_version": first("mcuVersion", "mcu_version", "MCU"),
        "firmware": firmware,
        "package": package,
        "sha256": sha256,
        "raw": data,
    }


def main():
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: python brain.py '<firmware version>' | python brain.py --vehicle-json <file>"
        )

    if sys.argv[1] == "--vehicle-json":
        if len(sys.argv) != 3:
            raise SystemExit("Usage: python brain.py --vehicle-json <file>")
        vehicle = load_vehicle_export(sys.argv[2])
        firmware = vehicle["firmware"]
    else:
        vehicle = {"firmware": sys.argv[1]}
        firmware = sys.argv[1]

    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    candidates = []

    for app in data.get("apps", []):
        ok, reason = compatible(app, firmware)
        if ok is True and app.get("source"):
            candidates.append({
                "id": app["id"],
                "name": app["name"],
                "source": app["source"],
                "reason": reason
            })

    result = {
        "target": data.get("target", {}),
        "vehicle_export": vehicle,
        "candidates": candidates,
        "automatic_install_allowed": False,
        "decision": (
            "compatible_candidate_found"
            if candidates else
            "no_verified_compatible_package"
        ),
        "next_step": (
            "Use the head-unit's supported installation mechanism only after "
            "the package source and checksum are independently verified."
        ),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
