"""Build a review-only catalog from observed software inventory and gap evidence.

This module deliberately does not import or mutate CapabilityRegistry. Catalog
entries are candidates, never ONLINE executors. Runtime promotion requires a
separate, explicit evidence-backed workflow.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .software_capability_gap_audit import audit as audit_capabilities
from .software_node_discovery import discover

SCHEMA_VERSION = "brain-software-capability-candidate-catalog/v1"

PROMOTION_REQUIREMENTS = {
    "local_python_runtime": ["bounded runtime smoke test", "captured exit status and interpreter identity"],
    "brain_tool_foundry": ["Tool Foundry contract tests", "security review of proposed tool permissions"],
    "media_transcoding": ["FFmpeg and FFprobe presence", "bounded sample transcode and probe"],
    "android_bridge": ["ADB version check", "explicitly authorized device identity and connectivity evidence"],
    "rtl_simulation": ["supported simulator version", "bounded known-good RTL simulation result"],
    "windows_virtualization_tools": ["QEMU tool versions", "bounded disposable VM smoke test without production resources"],
    "remote_device_execution": ["live device identity", "successful authentication/attestation", "fresh heartbeat", "bounded task result"],
    "physical_mining": ["independent live pool worker telemetry", "matching physical-device evidence", "fresh hashrate evidence"],
}


def build_catalog(
    inventory: dict[str, Any] | None = None,
    capability_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create candidate records without registering or activating executors."""
    inventory = discover() if inventory is None else inventory
    capability_report = audit_capabilities(inventory) if capability_report is None else capability_report

    capabilities = capability_report.get("capabilities", [])
    nodes = []
    for capability in capabilities:
        capability_id = capability.get("capability_id")
        status = capability.get("status", "UNKNOWN")
        observed = bool(capability.get("observed_present", False))
        if status == "BLOCKED_NEEDS_EXTERNAL_EVIDENCE":
            candidate_state = "BLOCKED_NEEDS_EVIDENCE"
        elif status == "MISSING_LOCAL_REQUIREMENT":
            candidate_state = "GAP"
        elif observed:
            candidate_state = "DISCOVERED_NOT_RUNTIME_VERIFIED"
        else:
            candidate_state = "UNCLASSIFIED_REQUIRES_REVIEW"
        nodes.append({
            "node_id": capability_id,
            "description": capability.get("description", ""),
            "candidate_state": candidate_state,
            "observed_present": observed,
            "evidence_level": capability.get("evidence_level", "UNSPECIFIED"),
            "source_status": status,
            "executor_state": "NOT_REGISTERED",
            "registration_allowed_by_this_report": False,
            "promotion_requirements": PROMOTION_REQUIREMENTS.get(
                capability_id, ["define a capability-specific verification contract"]
            ),
        })

    return {
        "schema": SCHEMA_VERSION,
        "mode": "REVIEW_ONLY_NO_REGISTRATION",
        "inventory_schema": inventory.get("schema"),
        "capability_report_schema": capability_report.get("schema"),
        "capability_registry_mutated": False,
        "capability_registry_imported": False,
        "generated_code_executed": False,
        "network_probed": False,
        "executor_online_claimed": False,
        "node_count": len(nodes),
        "nodes": nodes,
        "interpretation": (
            "Catalog entries are candidate classifications only. Discovery does not make an executor "
            "ONLINE; a separate evidence-backed promotion gate and explicit registration are required."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build Brain's review-only software capability candidate catalog")
    parser.add_argument("--output", help="write JSON to a new file; existing files are never overwritten")
    args = parser.parse_args(argv)
    report = build_catalog()
    rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        destination = Path(args.output)
        if destination.exists():
            parser.error(f"refusing to overwrite existing file: {destination}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(rendered)
        print(json.dumps({"ok": True, "output": str(destination), "node_count": report["node_count"]}))
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
