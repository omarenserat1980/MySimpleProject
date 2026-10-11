"""Evidence-gated pathway planner for Electronic Brain.

This module chooses the next safe step from a declared pathway and normalized
evidence. It does not execute privileged actions or manufacture evidence.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

PATHWAYS: dict[str, dict[str, Any]] = {
    "code_delivery": {
        "description": "Source change from inspection to verified integration.",
        "gates": [
            ("source_snapshot", "Capture the exact base/head commit and working-tree state."),
            ("plan_reviewed", "Record a scoped plan and identify affected interfaces."),
            ("tests_passed", "Run focused tests and the relevant regression suite."),
            ("security_review", "Check permissions, secrets handling, and unsafe side effects."),
            ("verification_evidence", "Attach inspectable test and review evidence to this change."),
            ("integration_verified", "Confirm required checks and merge/integration state."),
        ],
    },
    "windows_real_boot": {
        "description": "Prove Windows Server 2025 booted from the installed disk in one authorized run.",
        "gates": [
            ("signed_contract", "Obtain and validate the real pre-issued execution contract."),
            ("trusted_executor", "Verify executor identity, attestation, authority, and capability."),
            ("runner_execution", "Verify runner labels, runtime surface, and an actual execution probe."),
            ("installed_disk_identity", "Record the installed disk identity for this run."),
            ("guest_boot", "Collect guest-side Windows Server 2025 boot evidence from the installed disk."),
            ("same_run_binding", "Bind contract, executor, disk, guest evidence, and workflow run together."),
            ("completion_gate", "Pass the independent Windows completion gate using the same-run evidence."),
        ],
    },
    "media_factory": {
        "description": "Produce a media artifact with technical and cinematic quality gates.",
        "gates": [
            ("creative_brief", "Freeze the brief, target audience, format, and runtime."),
            ("asset_manifest", "Verify asset provenance and completeness."),
            ("render_integrity", "Verify output file, codecs, streams, dimensions, and duration."),
            ("cinematic_qc", "Pass cinematic quality checks; technical validity alone is insufficient."),
            ("content_review", "Review narrative continuity, audio, captions, and visual quality."),
            ("publish_authorization", "Require explicit publication authorization before external upload."),
        ],
    },
    "deployment": {
        "description": "Deploy a tested Brain service with recovery and runtime evidence.",
        "gates": [
            ("configuration_ready", "Validate configuration without exposing secret values."),
            ("tests_passed", "Pass relevant automated tests."),
            ("rollback_ready", "Verify a recoverable previous version or checkpoint."),
            ("deployment_authorized", "Verify authority and target scope before deployment."),
            ("health_verified", "Pass post-deployment health and smoke checks."),
            ("runtime_evidence", "Store deployment identity and post-deploy evidence."),
        ],
    },
    "recovery": {
        "description": "Restore a Brain checkpoint without destroying the current recovery path.",
        "gates": [
            ("checkpoint_found", "Identify the exact checkpoint and its provenance."),
            ("integrity_verified", "Verify checksum/signature and required files."),
            ("rollback_point_saved", "Create and verify a separate pre-restore rollback point."),
            ("restore_dry_run", "Run a non-destructive restore validation."),
            ("restore_authorized", "Verify authorization and target scope."),
            ("post_restore_verified", "Verify service readiness and critical invariants after restore."),
        ],
    },
}


def _valid_evidence(item: Any, gate_id: str, expected_run_id: str | None) -> tuple[bool, str]:
    if not isinstance(item, dict):
        return False, "EVIDENCE_MISSING"
    if item.get("verified") is not True:
        return False, "EVIDENCE_NOT_VERIFIED"
    for field in ("evidence_id", "source", "observed_at"):
        if not isinstance(item.get(field), str) or not item[field].strip():
            return False, "EVIDENCE_PROVENANCE_INCOMPLETE"
    if gate_id == "signed_contract" and item.get("signature_valid") is not True:
        return False, "CONTRACT_SIGNATURE_NOT_VERIFIED"
    if gate_id == "trusted_executor" and not all(item.get(k) is True for k in ("attestation_valid", "authority_valid", "capability_valid")):
        return False, "EXECUTOR_TRUST_CHAIN_INCOMPLETE"
    if gate_id == "runner_execution" and not all(item.get(k) is True for k in ("runner_online", "execution_probe_passed", "runtime_surface_passed")):
        return False, "RUNNER_EXECUTION_NOT_PROVEN"
    if gate_id == "installed_disk_identity" and not item.get("installed_disk_id"):
        return False, "INSTALLED_DISK_ID_MISSING"
    if gate_id == "guest_boot" and (item.get("os_name") != "Windows Server 2025" or item.get("boot_source") != "installed_disk"):
        return False, "INSTALLED_DISK_BOOT_NOT_PROVEN"
    if gate_id == "same_run_binding":
        if not item.get("run_id") or not item.get("contract_id") or not item.get("installed_disk_id"):
            return False, "SAME_RUN_BINDING_INCOMPLETE"
        if expected_run_id and item.get("run_id") != expected_run_id:
            return False, "WORKFLOW_RUN_MISMATCH"
    if gate_id == "publish_authorization" and item.get("authorized") is not True:
        return False, "PUBLICATION_NOT_AUTHORIZED"
    if gate_id == "deployment_authorized" and item.get("authorized") is not True:
        return False, "DEPLOYMENT_NOT_AUTHORIZED"
    if gate_id == "restore_authorized" and item.get("authorized") is not True:
        return False, "RESTORE_NOT_AUTHORIZED"
    return True, "VERIFIED"


def evaluate_pathway(pathway_id: str, evidence: dict[str, Any], expected_run_id: str | None = None) -> dict[str, Any]:
    if pathway_id not in PATHWAYS:
        raise ValueError(f"unknown_pathway:{pathway_id}")
    spec = PATHWAYS[pathway_id]
    gates = []
    blockers = []
    next_gate = None
    for gate_id, action in spec["gates"]:
        ok, reason = _valid_evidence(evidence.get(gate_id), gate_id, expected_run_id)
        row = {"gate": gate_id, "status": "VERIFIED" if ok else "BLOCKED", "reason": reason}
        gates.append(row)
        if not ok:
            blockers.append({"gate": gate_id, "code": reason, "next_action": action})
            if next_gate is None:
                next_gate = gate_id
    ready = not blockers
    return {
        "schema": "brain.pathway-evaluation.v1",
        "pathway": pathway_id,
        "status": "READY" if ready else "BLOCKED",
        "ready": ready,
        "next_gate": next_gate,
        "gates": gates,
        "blockers": blockers,
        "policy": "Evidence only; no actions executed; missing or unproven gates remain blocked.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate a Brain pathway against normalized evidence JSON.")
    parser.add_argument("--pathway", choices=sorted(PATHWAYS), required=True)
    parser.add_argument("--evidence", required=True, help="JSON object keyed by pathway gate ID")
    parser.add_argument("--expected-run-id", help="Require same-run binding for the Windows real-boot pathway")
    parser.add_argument("--output", default="brain-pathway-evaluation.json")
    args = parser.parse_args()
    try:
        evidence = json.loads(Path(args.evidence).read_text(encoding="utf-8-sig"))
        if not isinstance(evidence, dict):
            raise ValueError("evidence_root_must_be_object")
        result = evaluate_pathway(args.pathway, evidence, args.expected_run_id)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        result = {
            "schema": "brain.pathway-evaluation.v1",
            "pathway": args.pathway,
            "status": "BLOCKED",
            "ready": False,
            "next_gate": None,
            "gates": [],
            "blockers": [{"gate": "input", "code": "INPUT_INVALID", "next_action": str(exc)}],
            "policy": "Invalid input is blocked; no actions executed.",
        }
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
