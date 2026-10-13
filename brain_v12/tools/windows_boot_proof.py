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
                expected_run_id: str, guest_evidence_path: Path | None = None,
                trusted_iso_sha256: str = "") -> dict[str, Any]:
    reasons: list[str] = []
    try:
        evidence = _json(evidence_path)
        guest_evidence = _json(guest_evidence_path) if guest_evidence_path else {}
        contract_gate = _json(contract_gate_path)
        executor_gate = _json(executor_gate_path)
        marker = marker_path.read_text(encoding="utf-8-sig").strip()
        phase = phase_path.read_text(encoding="utf-8")
    except (ValueError, OSError) as exc:
        reasons.append(str(exc))
        evidence = {}
        guest_evidence = {}
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

    # Validate the untouched guest-written file independently of the host-enriched
    # combined evidence. Host-side fields must never substitute for guest evidence.
    if guest_evidence_path is not None:
        raw_guest = guest_evidence.get("guest") or {}
        raw_network = guest_evidence.get("network") or {}
        raw_storage = guest_evidence.get("storage") or {}
        if guest_evidence.get("schema") != "BRAIN-WINDOWS-BOOT-EVIDENCE-1":
            reasons.append("RAW_GUEST_EVIDENCE_SCHEMA_INVALID")
        if guest_evidence.get("status") != "WINDOWS_BOOT_VERIFIED":
            reasons.append("RAW_GUEST_EVIDENCE_STATUS_INVALID")
        if raw_guest.get("os") != "Windows Server 2025" or raw_guest.get("boot_verified") is not True:
            reasons.append("RAW_GUEST_OS_BOOT_NOT_PROVEN")
        if raw_guest.get("architecture") not in {"AMD64", "x86_64"}:
            reasons.append("RAW_GUEST_ARCHITECTURE_INVALID")
        if not raw_guest.get("boot_time") or not raw_guest.get("version") or not raw_guest.get("build"):
            reasons.append("RAW_GUEST_BOOT_METADATA_MISSING")
        if raw_network.get("adapter_up") is not True or raw_network.get("internet_443") is not True:
            reasons.append("RAW_GUEST_NETWORK_NOT_VERIFIED")
        if not raw_storage.get("filesystem") or int(raw_storage.get("size_bytes") or 0) < 32 * 1024**3:
            reasons.append("RAW_GUEST_SYSTEM_DISK_NOT_VERIFIED")

    trusted_hash = str(trusted_iso_sha256 or "").strip().lower()
    media_hash = str((evidence.get("media") or {}).get("sha256", "")).strip().lower()
    if trusted_hash:
        if len(trusted_hash) != 64 or any(c not in "0123456789abcdef" for c in trusted_hash):
            reasons.append("TRUSTED_ISO_SHA256_INVALID")
        elif media_hash != trusted_hash:
            reasons.append("TRUSTED_ISO_SHA256_MISMATCH")

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

    try:
        base_gate = WindowsCompletionGate().verify(evidence) if evidence else {
            "status": "INCOMPLETE", "verified": False, "reasons": ["EVIDENCE_UNAVAILABLE"],
            "evidence_sha256": hashlib.sha256(b"").hexdigest(),
        }
    except Exception as exc:
        # Malformed evidence must fail closed with a sanitized type-only reason.
        base_gate = {
            "status": "INCOMPLETE", "verified": False,
            "reasons": ["COMPLETION_GATE_EXCEPTION:" + type(exc).__name__],
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
    parser.add_argument("--guest-evidence", default="windows-boot-evidence.json",
                        help="Untouched JSON written by the Windows guest onto the evidence disk.")
    parser.add_argument("--trusted-iso-sha256", default=os.environ.get("TRUSTED_ISO_SHA256_INPUT", ""),
                        help="Independently verified Microsoft SHA-256 for the downloaded ISO.")
    parser.add_argument("--output", default="windows-boot-proof.json")
    args = parser.parse_args()

    result = verify_boot(
        evidence_path=Path(args.evidence), marker_path=Path(args.marker),
        phase_path=Path(args.phase), contract_gate_path=Path(args.contract_gate),
        executor_gate_path=Path(args.executor_gate), expected_run_id=args.run_id,
        guest_evidence_path=Path(args.guest_evidence),
        trusted_iso_sha256=args.trusted_iso_sha256,
    )
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["verified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
