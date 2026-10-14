"""Validate a commit-bound, externally collected Brain runtime evidence manifest.

This module validates supplied observations only. It does not probe services,
execute components, contact devices, or turn missing evidence into a pass.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

RESULTS = {"PASS", "FAIL", "BLOCKED", "NOT_RUN"}
TOP_FIELDS = {"schema_version", "source_revision", "generated_utc", "components"}
COMPONENT_FIELDS = {
    "component_id", "domain", "required", "result", "source_revision",
    "check_id", "reference", "observed_utc", "exit_status", "scope",
    "limitations",
}


def validate_manifest(manifest: Any) -> tuple[list[str], str, dict[str, int]]:
    """Return structural errors, gate status, and result counts."""
    errors: list[str] = []
    counts = {result: 0 for result in sorted(RESULTS)}
    if not isinstance(manifest, dict):
        return ["manifest must be a JSON object"], "INVALID", counts

    missing = sorted(TOP_FIELDS - manifest.keys())
    if missing:
        return [f"missing top-level fields: {', '.join(missing)}"], "INVALID", counts
    if manifest["schema_version"] != 1:
        errors.append("schema_version must equal 1")
    revision = manifest["source_revision"]
    if not isinstance(revision, str) or not revision.strip():
        errors.append("source_revision must be a non-empty commit or immutable revision")
    if not isinstance(manifest["generated_utc"], str) or not manifest["generated_utc"].strip():
        errors.append("generated_utc must be a non-empty UTC timestamp")
    components = manifest["components"]
    if not isinstance(components, list) or not components:
        errors.append("components must be a non-empty list")
        return errors, "INVALID", counts

    seen: set[str] = set()
    required_results: list[str] = []
    for index, component in enumerate(components):
        prefix = f"components[{index}]"
        if not isinstance(component, dict):
            errors.append(f"{prefix} must be an object")
            continue
        absent = sorted(COMPONENT_FIELDS - component.keys())
        if absent:
            errors.append(f"{prefix} missing fields: {', '.join(absent)}")
            continue

        component_id = component["component_id"]
        if not isinstance(component_id, str) or not component_id.strip():
            errors.append(f"{prefix}.component_id must be non-empty")
        elif component_id in seen:
            errors.append(f"duplicate component_id: {component_id}")
        else:
            seen.add(component_id)

        for field in ("domain", "check_id", "reference", "observed_utc", "scope", "limitations"):
            if not isinstance(component[field], str) or not component[field].strip():
                errors.append(f"{prefix}.{field} must be a non-empty string")
        if not isinstance(component["required"], bool):
            errors.append(f"{prefix}.required must be boolean")
        result = component["result"]
        if not isinstance(result, str) or result not in RESULTS:
            errors.append(f"{prefix}.result must be one of {sorted(RESULTS)}")
            continue
        counts[result] += 1
        if isinstance(revision, str) and revision.strip() and component["source_revision"] != revision:
            errors.append(f"{prefix}.source_revision does not match manifest source_revision")

        exit_status = component["exit_status"]
        if result == "PASS" and (not isinstance(exit_status, int) or isinstance(exit_status, bool) or exit_status != 0):
            errors.append(f"{prefix} PASS requires integer exit_status 0")
        elif result == "FAIL" and (not isinstance(exit_status, int) or isinstance(exit_status, bool) or exit_status == 0):
            errors.append(f"{prefix} FAIL requires a non-zero integer exit_status")
        elif result in {"BLOCKED", "NOT_RUN"} and exit_status is not None:
            errors.append(f"{prefix} {result} requires exit_status null")
        if component["required"] is True:
            required_results.append(result)

    if errors:
        return errors, "INVALID", counts
    if "FAIL" in required_results:
        return errors, "FAIL", counts
    if any(result in {"BLOCKED", "NOT_RUN"} for result in required_results):
        return errors, "BLOCKED", counts
    return errors, "READY", counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="path to runtime evidence manifest JSON")
    args = parser.parse_args()
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "INVALID", "errors": [str(exc)], "counts": {}}, ensure_ascii=False))
        return 2

    errors, status, counts = validate_manifest(manifest)
    output = {"status": status, "component_count": len(manifest.get("components", [])) if isinstance(manifest, dict) and isinstance(manifest.get("components"), list) else 0,
              "counts": counts, "errors": errors,
              "note": "Manifest validation checks supplied evidence only; it does not execute or independently verify components."}
    print(json.dumps(output, ensure_ascii=False, sort_keys=True))
    return 0 if status == "READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
