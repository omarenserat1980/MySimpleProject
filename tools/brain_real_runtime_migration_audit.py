#!/usr/bin/env python3
"""Audit the Electronic Brain simulator-to-real migration backlog.

This is a source/evidence contract audit, not a live-service probe. It never
starts services, creates cloud resources, sends email, publishes media, or
submits transactions. It intentionally never promotes a component to LIVE.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = ROOT / "config" / "real_runtime_migration.json"
NON_LIVE_STATUSES = {
    "IMPLEMENTED_UNVERIFIED",
    "SIMULATOR_ONLY",
    "INTEGRATION_NOT_IMPLEMENTED",
    "EXTERNAL_AUTH_AND_COST_GATE_REQUIRED",
    "EXTERNAL_AUTH_REQUIRED",
    "EXTERNAL_AUTH_AND_RECEIPT_REQUIRED",
    "NOT_PROVEN",
}


def build_report(inventory: dict[str, Any], root: Path = ROOT) -> dict[str, Any]:
    components = []
    for item in inventory.get("components", []):
        paths = item.get("code_paths", [])
        present = [p for p in paths if (root / p).exists()]
        missing = [p for p in paths if not (root / p).exists()]
        declared_status = str(item.get("status", "NOT_PROVEN"))
        components.append({
            "id": item["id"],
            "name": item["name"],
            "declared_status": declared_status,
            "status": declared_status,
            "code_paths_present": present,
            "code_paths_missing": missing,
            "source_presence_is_runtime_proof": False,
            "real_acceptance": item.get("real_acceptance", []),
            "note": item.get("note", ""),
        })
    return {
        "schema": "electronic-brain.real-runtime-migration-report.v1",
        "mode": "read_only_source_audit",
        "live_status_claimed": False,
        "policy": inventory.get("policy", {}),
        "component_count": len(components),
        "non_live_component_count": sum(
            component["status"] in NON_LIVE_STATUSES for component in components
        ),
        "components": components,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument("--output", help="optional JSON report path")
    args = parser.parse_args()
    inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    report = build_report(inventory)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        output = Path(args.output).expanduser()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    if args.json or args.output:
        print(rendered, end="")
    else:
        print("Brain real-runtime migration audit (source-only; no live claims)")
        for component in report["components"]:
            missing = f"; missing source paths: {', '.join(component['code_paths_missing'])}" if component["code_paths_missing"] else ""
            print(f"- {component['id']}: {component['status']}{missing}")
        print(f"Components: {report['component_count']}; non-live/unverified: {report['non_live_component_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
