"""Fail-closed readiness audit for Electronic Brain's Golden Closed Loop.

This module audits an evidence snapshot supplied by real Brain/GitHub/runtime
probes. It never probes services itself and never converts missing evidence into
success. All critical facts must be literal booleans/values from trusted
producers; a simulation or a successful workflow alone is not real-boot proof.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REQUIRED_RUNNER_LABELS = {
    "self-hosted", "linux", "x64", "brain-internal", "qemu",
    "windows-real-boot", "brain-cloud-executor",
}

# Every entry is an exact proof obligation. Only literal True satisfies boolean
# requirements; strings such as "true", "PASS", or non-empty objects do not.
REQUIRED_TRUE = {
    "repository.required_ci_passed": "Required CI checks must pass for the audited commit.",
    "repository.source_commit_bound": "Evidence must identify the exact source commit.",
    "runner.secret_configured": "BRAIN_RUNNER_WATCH_TOKEN must be configured without exposing its value.",
    "runner.api_read_succeeded": "Runner administration API must return without permission errors.",
    "runner.online": "A real self-hosted runner must be online.",
    "runner.execution_probe_passed": "The runner must execute the explicit capability probe.",
    "runner.runtime_surface_passed": "The runner runtime surface must pass its probe.",
    "contract.control_plane_issued": "The execution contract must be issued by the authorized Control Plane.",
    "contract.signature_verified": "The contract signature must verify against the trusted key.",
    "contract.source_commit_matches": "The contract must bind to the exact audited source commit.",
    "contract.lease_valid": "The contract lease/fencing token must be valid.",
    "contract.not_expired": "The contract must not be expired.",
    "contract.capability_authorized": "The requested capability must be authorized by the contract.",
    "executor.attestation_verified": "Cloud Executor attestation must verify cryptographically.",
    "executor.same_runner_as_boot": "Attestation and boot evidence must come from the same designated runner.",
    "executor.qemu_kvm_available": "The real executor must report QEMU/KVM capability.",
    "windows.iso_validated": "The Windows Server 2025 ISO must pass integrity and edition checks.",
    "windows.installed_disk_boot_verified": "Evidence must prove Windows booted from the installed disk.",
    "windows.guest_identity_verified": "Guest evidence must verify the intended Windows Server 2025 identity.",
    "windows.guest_health_verified": "Guest health checks must pass after boot.",
    "evidence.hashes_verified": "Evidence hashes and chain integrity must verify.",
    "evidence.independent_verifier_passed": "A verifier independent from the executor must pass.",
    "evidence.persisted_and_reopen_verified": "Evidence must survive process restart and be readable again.",
    "recovery.restart_recovery_tested": "Restart/recovery behavior must be exercised and verified.",
    "recovery.idempotency_verified": "Retries must not duplicate a fenced execution.",
    "recovery.rollback_ready": "A verified rollback/recovery path must be available.",
    "governance.owner_approval_verified": "Owner approval must be verified and scoped to this exact capability.",
    "governance.cost_gate_passed": "Cost policy must explicitly permit the planned operation.",
    "governance.stop_switch_tested": "The emergency stop path must be verified.",
}


def _get(snapshot: dict[str, Any], dotted_path: str) -> Any:
    value: Any = snapshot
    for part in dotted_path.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def audit_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Return a deterministic gate report. Missing or malformed evidence blocks."""
    if not isinstance(snapshot, dict):
        return {
            "ok": False,
            "status": "GOLDEN_LOOP_BLOCKED",
            "reason": "SNAPSHOT_MUST_BE_OBJECT",
            "blockers": ["SNAPSHOT_MUST_BE_OBJECT"],
            "passed": [],
            "checked_at_source": None,
        }

    blockers: list[str] = []
    passed: list[str] = []
    details: dict[str, str] = {}

    source_commit = _get(snapshot, "repository.commit_sha")
    if not isinstance(source_commit, str) or len(source_commit) not in (40, 64) or any(
        c not in "0123456789abcdefABCDEF" for c in source_commit
    ):
        blockers.append("REPOSITORY_COMMIT_SHA_INVALID")
        details["repository.commit_sha"] = "A full 40- or 64-character hexadecimal commit SHA is required."
    else:
        passed.append("repository.commit_sha")

    for path, description in REQUIRED_TRUE.items():
        if _get(snapshot, path) is True:
            passed.append(path)
        else:
            blockers.append(path.upper().replace(".", "_") + "_REQUIRED")
            details[path] = description

    labels = _get(snapshot, "runner.labels")
    if not isinstance(labels, list) or not all(isinstance(label, str) for label in labels):
        blockers.append("RUNNER_REQUIRED_LABELS_MISSING")
        details["runner.labels"] = "Runner labels must be a list containing all required labels."
    else:
        missing_labels = sorted(REQUIRED_RUNNER_LABELS - set(labels))
        if missing_labels:
            blockers.append("RUNNER_REQUIRED_LABELS_MISSING")
            details["runner.labels"] = "Missing labels: " + ", ".join(missing_labels)
        else:
            passed.append("runner.labels")

    reality = _get(snapshot, "windows.reality")
    if reality != "REAL":
        blockers.append("REAL_WINDOWS_EVIDENCE_REQUIRED")
        details["windows.reality"] = "Only literal REAL evidence is admissible; SIMULATED/TWIN is not real boot."
    else:
        passed.append("windows.reality")

    evidence_commit = _get(snapshot, "evidence.source_commit_sha")
    if not isinstance(source_commit, str) or evidence_commit != source_commit:
        blockers.append("EVIDENCE_SOURCE_COMMIT_MISMATCH")
        details["evidence.source_commit_sha"] = "Evidence must be bound to the exact audited repository commit."
    else:
        passed.append("evidence.source_commit_sha")

    contract_commit = _get(snapshot, "contract.source_commit_sha")
    if not isinstance(source_commit, str) or contract_commit != source_commit:
        blockers.append("CONTRACT_SOURCE_COMMIT_MISMATCH")
        details["contract.source_commit_sha"] = "The contract source commit must exactly match the audited commit."
    else:
        passed.append("contract.source_commit_sha")

    # A CI success label alone cannot substitute for the independent evidence
    # and real-guest obligations above. A status field is informational only.
    blockers = sorted(set(blockers))
    passed = sorted(set(passed))
    ok = not blockers
    return {
        "ok": ok,
        "status": "GOLDEN_LOOP_READY_FOR_CLOSURE" if ok else "GOLDEN_LOOP_BLOCKED",
        "source_commit_sha": source_commit if isinstance(source_commit, str) else None,
        "passed_count": len(passed),
        "required_count": len(REQUIRED_TRUE) + 5,
        "passed": passed,
        "blockers": blockers,
        "details": details,
        "next_action": "ALLOW_CLOSURE_REVIEW" if ok else "REPAIR_BLOCKERS_THEN_RERUN_AUDIT",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit evidence for Golden Closed Loop readiness.")
    parser.add_argument("snapshot", help="JSON evidence snapshot from trusted Brain probes")
    parser.add_argument("--output", help="Optional JSON report path")
    args = parser.parse_args(argv)
    try:
        snapshot = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        report = {
            "ok": False,
            "status": "GOLDEN_LOOP_BLOCKED",
            "blockers": ["SNAPSHOT_LOAD_FAILED"],
            "details": {"snapshot": str(exc)},
        }
    else:
        report = audit_snapshot(snapshot)
    rendered = json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if report.get("ok") is True else 2


if __name__ == "__main__":
    raise SystemExit(main())
