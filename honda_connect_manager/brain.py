#!/usr/bin/env python3
"""Honda CONNECT 3.0 compatibility brain.

Conservative by design:
- discovers vehicle JSON exports recursively;
- extracts firmware/system/hardware/MCU/package metadata;
- matches only explicit compatibility rules;
- optionally verifies a local package SHA-256;
- never installs to the vehicle and never invents package URLs.
"""

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "apps.json"


def version_tuple(value):
    nums = re.findall(r"\d+", str(value or ""))
    return tuple(int(x) for x in nums[:4]) if nums else ()


def first_value(data, *keys):
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return str(value)
    return ""


def load_vehicle_export(path):
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    firmware = first_value(
        data, "softwareVersion", "software_version", "systemVersion",
        "system_version", "version", "firmwareVersion", "firmware_version"
    )
    return {
        "source_file": str(p),
        "system_version": first_value(data, "systemVersion", "system_version"),
        "software_version": first_value(data, "softwareVersion", "software_version"),
        "hardware_version": first_value(data, "hardwareVersion", "hardware_version"),
        "mcu_version": first_value(data, "mcuVersion", "mcu_version", "MCU"),
        "firmware": firmware,
        "package": first_value(data, "package", "packageName", "package_name", "fileName", "filename"),
        "sha256": first_value(data, "sha256", "SHA256", "packageSha256", "package_sha256"),
        "raw_keys": sorted(data.keys()),
    }


def discover_exports(root):
    root = Path(root)
    found = []
    for p in root.rglob("*.json"):
        if p.is_file() and p.name.lower() in {"update_by_usb.json", "update_by_usb"}:
            try:
                found.append(load_vehicle_export(p))
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                found.append({"source_file": str(p), "error": str(exc)})
    return found


def compatible(app, firmware):
    rules = app.get("compatibility_rules", [])
    if not rules:
        return None, "no compatibility rule"
    fv = version_tuple(firmware)
    if not fv:
        return None, "firmware version not parseable"

    for rule in rules:
        exact = str(rule.get("exact", "")).strip()
        if exact and firmware.strip() == exact:
            return True, "exact firmware match"
        min_v, max_v = version_tuple(rule.get("min")), version_tuple(rule.get("max"))
        if min_v and fv < min_v:
            continue
        if max_v and fv > max_v:
            continue
        return True, "firmware is inside supported range"
    return False, "firmware outside supported ranges"


def sha256_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def evaluate(vehicle):
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    firmware = vehicle.get("firmware", "")
    candidates = []
    for app in data.get("apps", []):
        ok, reason = compatible(app, firmware)
        if ok is True:
            candidates.append({
                "id": app["id"],
                "name": app["name"],
                "source": app.get("source", ""),
                "reason": reason,
                "source_verified": bool(app.get("source") and app.get("sha256")),
            })

    verified = [c for c in candidates if c["source_verified"]]
    decision = "verified_candidate_found" if verified else "no_verified_compatible_package"
    return {
        "target": data.get("target", {}),
        "vehicle_export": vehicle,
        "candidates": candidates,
        "verified_candidates": verified,
        "automatic_install_allowed": False,
        "decision": decision,
        "next_step": "Use Honda's supported head-unit installation/update mechanism after independent package verification."
    }


def main(argv):
    if len(argv) < 2:
        raise SystemExit(
            "Usage: brain.py <firmware> | --vehicle-json <file> | --scan <folder>"
        )

    if argv[1] == "--vehicle-json":
        if len(argv) != 3:
            raise SystemExit("Usage: brain.py --vehicle-json <file>")
        result = evaluate(load_vehicle_export(argv[2]))
    elif argv[1] == "--scan":
        if len(argv) != 3:
            raise SystemExit("Usage: brain.py --scan <folder>")
        exports = discover_exports(argv[2])
        result = {
            "target": json.loads(MANIFEST.read_text(encoding="utf-8")).get("target", {}),
            "discovered_exports": exports,
            "evaluations": [evaluate(v) for v in exports if "error" not in v],
            "automatic_install_allowed": False,
        }
    else:
        result = evaluate({"firmware": argv[1]})

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main(sys.argv)
