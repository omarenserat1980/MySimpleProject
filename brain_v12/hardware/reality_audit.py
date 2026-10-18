"""Fail-closed structural audit of Brain hardware integration claims.

This validates registry declarations only. It does not authenticate external
artifacts or prove a tool/device exists.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ALLOWED = {
    "PLANNED", "ADAPTER_IMPLEMENTED", "TOOL_EXECUTION_VERIFIED",
    "SIMULATION_VERIFIED", "HOST_EVIDENCE_RECORDED",
    "PHYSICAL_HARDWARE_VERIFIED", "BLOCKED",
}
REQUIRED = {"id", "name", "reality_status", "evidence", "not_proven", "next_gate"}


def audit_registry(data: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if data.get("schema_version") != 1:
        errors.append("schema_version must equal 1")
    policy = data.get("audit_policy")
    if not isinstance(policy, dict) or policy.get("never_infer_physical_hardware_from_simulation") is not True:
        errors.append("physical-claim policy must fail closed")
    components = data.get("components")
    if not isinstance(components, list):
        components = []
        errors.append("components must be a list")
    seen: set[str] = set()
    for index, item in enumerate(components):
        if not isinstance(item, dict):
            errors.append(f"components[{index}] must be an object")
            continue
        missing = REQUIRED - item.keys()
        if missing:
            errors.append(f"components[{index}] missing: {','.join(sorted(missing))}")
        component_id = item.get("id")
        if not isinstance(component_id, str) or not component_id.strip():
            errors.append(f"components[{index}] has invalid id")
        elif component_id in seen:
            errors.append(f"duplicate component id: {component_id}")
        else:
            seen.add(component_id)
        status = item.get("reality_status")
        if status not in ALLOWED:
            errors.append(f"{component_id}: unknown reality_status {status!r}")
        for field in ("evidence", "not_proven"):
            if not isinstance(item.get(field), list) or any(not isinstance(v, str) for v in item.get(field, [])):
                errors.append(f"{component_id}: {field} must be a list of strings")
        if status == "PHYSICAL_HARDWARE_VERIFIED":
            if not item.get("evidence") or not item.get("next_gate"):
                errors.append(f"{component_id}: physical claim requires evidence references and verifier gate")
            if not item.get("independent_verification_ref"):
                errors.append(f"{component_id}: physical claim requires independent_verification_ref")
    return {
        "schema_version": 1,
        "component_count": len(components),
        "passed": not errors,
        "errors": errors,
        "claim_boundary": "Structural registry validation only; no external evidence or physical device is authenticated.",
    }


def audit_file(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return audit_registry(data)
