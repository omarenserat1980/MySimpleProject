"""Fail-closed verifier whose sole purpose is proving a real Windows Server 2025 boot.

This tool does not start VMs, mint approvals, change permissions, or access secrets.
It consumes guest-written evidence and the same-run contract/executor evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from brain_v12.brain.windows_completion_gate import WindowsCompletionGate


def _json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise ValueError("EVIDENCE_FILE_MISSING:" + path.name) from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("EVIDENCE_FILE_INVALID:" + path.name) from exc
    if not isinstance(value, dict):
        raise ValueError("EVIDENCE_ROOT_NOT_OBJECT:" + path.name)
    return value


def verify_boot(*, evidence_path: Path, marker_path: Path, phase_path: Path,
                contract_gate_path: Path, executor_gate_path: Path,
                expected_run_id: str) -> dict[str, Any]:
    reasons: list[str] = []
    try:
        evidence = _json(evidence_path)
        contract_gate = _json(contract_gate_path)
        executor_gate = _json(executor_gate_path)
        marker = marker_path.read_text(encoding="utf-8-sig").strip()
        phase = phase_path.read_text(encoding="utf-8")
    except (ValueError, OSError) as exc:
        reasons.append(str(exc))
        evidence = {}
        contract_gate = {}
        executor_gate = {}
        marker = ""
        phase = ""

    if contract_gate.get("verified") is not True:
        reasons.append("CONTRACT_GATE_NOT_VERIFIED")
    if executor_gate.get("verified") is not True:
        reasons.append("EXECUTOR_GATE_NOT_VERIFIED")

    if marker != "WINDOWS_BOOT_VERIFIED":
        reasons.append("GUEST_BOOT_MARKER_INVALID")
    if "BOOT_PHASE=WINDOWS_INSTALLED_AND_BOOTED_FROM_DISK" not in phase:
        reasons.append("INSTALLED_DISK_BOOT_PHASE_MISSING")
    if "BOOT_SOURCE=windows-installed-disk" not in phase:
        reasons.append("INSTALLED_DISK_SOURCE_MISSING")

    guest = evidence.get("guest") or {}
    if evidence.get("schema") != "BRAIN-WINDOWS-BOOT-EVIDENCE-1":
        reasons.append("GUEST_EVIDENCE_SCHEMA_INVALID")
    if evidence.get("status") != "WINDOWS_BOOT_VERIFIED":
        reasons.append("GUEST_EVIDENCE_STATUS_INVALID")
    if guest.get("os") != "Windows Server 2025" or guest.get("boot_verified") is not True:
        reasons.append("GUEST_OS_BOOT_NOT_PROVEN")
    if guest.get("architecture") != "x86_64":
        reasons.append("GUEST_ARCHITECTURE_NOT_VERIFIED")
    if evidence.get("boot_source") != "windows-installed-disk":
        reasons.append("EVIDENCE_NOT_FROM_INSTALLED_DISK")

    executor = evidence.get("executor") or {}
    run_id = str(expected_run_id or os.environ.get("GITHUB_RUN_ID", "")).strip()
    if not run_id:
        reasons.append("EXPECTED_WORKFLOW_RUN_ID_MISSING")
    if str(executor.get("workflow_run_id", "")).strip() != run_id:
        reasons.append("WORKFLOW_RUN_ID_MISMATCH")
    if not executor.get("executor_id") or not executor.get("evidence_ref"):
        reasons.append("TRUSTED_EXECUTOR_EVIDENCE_MISSING")
    if str(executor.get("executor_id", "")).strip() != str(executor_gate.get("executor_id", "")).strip():
        reasons.append("EXECUTOR_ID_MISMATCH")
    if str(executor.get("evidence_ref", "")).strip() != str(executor_gate.get("evidence_ref", "")).strip():
        reasons.append("EXECUTOR_EVIDENCE_REF_MISMATCH")

    control = evidence.get("control") or {}
    contract = contract_gate.get("contract") or {}
    for field in ("schema", "status", "capability", "executor", "brain_id", "generation",
                  "fencing_token", "task_id", "attempt_id"):
        if control.get(field) != contract.get(field):
            reasons.append("CONTRACT_BINDING_MISMATCH:" + field)

    base_gate = WindowsCompletionGate().verify(evidence) if evidence else {
        "status": "INCOMPLETE", "verified": False, "reasons": ["EVIDENCE_UNAVAILABLE"],
        "evidence_sha256": hashlib.sha256(b"").hexdigest(),
    }
    if base_gate.get("verified") is not True:
        reasons.extend("COMPLETION_GATE:" + str(x) for x in base_gate.get("reasons", []))

    # Stable, non-secret evidence digest; never include contract contents or tokens.
    digest = hashlib.sha256(
        json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    reasons = list(dict.fromkeys(reasons))
    return {
        "schema": "brain.windows-boot-proof.v1",
        "status": "WINDOWS_BOOT_VERIFIED" if not reasons else "INCOMPLETE",
        "verified": not reasons,
        "workflow_run_id": run_id or None,
        "evidence_sha256": digest,
        "completion_gate_status": base_gate.get("status"),
        "reasons": reasons,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify only real Windows Server 2025 installed-disk boot evidence.")
    parser.add_argument("--evidence", default="windows-combined-evidence.json")
    parser.add_argument("--marker", default="/tmp/windows-boot-marker")
    parser.add_argument("--phase", default="windows-boot-phase.txt")
    parser.add_argument("--contract-gate", default="windows-execution-contract-gate.json")
    parser.add_argument("--executor-gate", default="cloud-executor-gate.json")
    parser.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID", ""))
    parser.add_argument("--output", default="windows-boot-proof.json")
    args = parser.parse_args()

    result = verify_boot(
        evidence_path=Path(args.evidence), marker_path=Path(args.marker),
        phase_path=Path(args.phase), contract_gate_path=Path(args.contract_gate),
        executor_gate_path=Path(args.executor_gate), expected_run_id=args.run_id,
    )
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["verified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
