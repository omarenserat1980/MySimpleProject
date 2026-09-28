#!/usr/bin/env python3
"""Honda CONNECT compatibility brain.

Input: exact Honda CONNECT firmware/version string plus apps.json.
Output: compatible package candidates, with a conservative decision:
- exact version match
- supported range match
- unknown => no automatic install
"""

import json, re, sys
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

def main(firmware):
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
        "firmware": firmware,
        "candidates": candidates,
        "automatic_install_allowed": False,
        "next_step": "Use a verified package source and the head-unit's supported installation mechanism."
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python brain.py '<Honda CONNECT firmware version>'")
    main(sys.argv[1])
