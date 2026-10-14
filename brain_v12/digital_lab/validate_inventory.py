"""Validate Brain Digital Lab inventory reports without probing assets.

This checks report structure and evidence-state consistency only. It does not
validate runtime health or treat discovery metadata as proof of operation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REQUIRED_TOP_LEVEL = {
    "schema_version", "inventory_type", "generated_utc", "repository_root",
    "commit_sha", "asset_count", "coverage_limitations", "assets",
}
REQUIRED_ASSET_FIELDS = {
    "asset_id", "path", "domain", "size_bytes", "modified_utc",
    "lifecycle_status", "verification_status", "evidence",
}

class InventoryValidationError(ValueError):
    """Raised when an inventory report is malformed or overstates verification."""

def validate_inventory(report: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(report, dict):
        return ["report must be a JSON object"]
    missing = sorted(REQUIRED_TOP_LEVEL - report.keys())
    if missing:
        errors.append(f"missing top-level fields: {', '.join(missing)}")
        return errors
    if report["schema_version"] != 1:
        errors.append("unsupported schema_version; expected 1")
    if report["inventory_type"] != "repository_path_metadata_only":
        errors.append("inventory_type must be repository_path_metadata_only")
    assets = report["assets"]
    if not isinstance(assets, list):
        return errors + ["assets must be a list"]
    if report["asset_count"] != len(assets):
        errors.append("asset_count does not match the assets list length")
    if not isinstance(report["coverage_limitations"], list) or not report["coverage_limitations"]:
        errors.append("coverage_limitations must be a non-empty list")
    seen: set[str] = set()
    for index, asset in enumerate(assets):
        prefix = f"assets[{index}]"
        if not isinstance(asset, dict):
            errors.append(f"{prefix} must be an object")
            continue
        absent = sorted(REQUIRED_ASSET_FIELDS - asset.keys())
        if absent:
            errors.append(f"{prefix} missing fields: {', '.join(absent)}")
            continue
        path = asset["path"]
        asset_id = asset["asset_id"]
        if not isinstance(path, str) or not path or path.startswith("/") or "\\" in path:
            errors.append(f"{prefix}.path must be a non-empty repository-relative POSIX path")
        elif any(part in {"", ".", ".."} for part in path.split("/")):
            errors.append(f"{prefix}.path contains an unsafe path segment")
        if asset_id != path:
            errors.append(f"{prefix}.asset_id must equal path")
        if isinstance(path, str):
            if path in seen:
                errors.append(f"duplicate asset path: {path}")
            seen.add(path)
        if not isinstance(asset["size_bytes"], int) or asset["size_bytes"] < 0:
            errors.append(f"{prefix}.size_bytes must be a non-negative integer")
        if asset["lifecycle_status"] not in {"DISCOVERED_NOT_TESTED", "IN_REVIEW", "ACCEPTED", "REJECTED", "QUARANTINED"}:
            errors.append(f"{prefix}.lifecycle_status is not recognized")
        if asset["verification_status"] not in {"NOT_RUN", "PASS", "FAIL", "BLOCKED", "NOT_APPLICABLE"}:
            errors.append(f"{prefix}.verification_status is not recognized")
        if asset["lifecycle_status"] == "DISCOVERED_NOT_TESTED" and asset["verification_status"] != "NOT_RUN":
            errors.append(f"{prefix} cannot claim verification before leaving DISCOVERED_NOT_TESTED")
        if not isinstance(asset["evidence"], list):
            errors.append(f"{prefix}.evidence must be a list")
    return errors

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inventory", type=Path, help="path to inventory JSON")
    args = parser.parse_args()
    try:
        report = json.loads(args.inventory.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "INVALID", "errors": [str(exc)]}, ensure_ascii=False))
        return 2
    errors = validate_inventory(report)
    print(json.dumps({"status": "VALID" if not errors else "INVALID",
                      "asset_count": report.get("asset_count") if isinstance(report, dict) else None,
                      "errors": errors}, ensure_ascii=False))
    return 0 if not errors else 2

if __name__ == "__main__":
    raise SystemExit(main())
