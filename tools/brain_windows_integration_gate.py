#!/usr/bin/env python3
"""Fail-closed integration gate for the Brain Windows Server 2025 real-boot path.

This tool is intentionally read-only. It validates repository wiring and required
security/evidence gates; it never creates approvals, issues contracts, downloads
media, or claims that Windows booted.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

TASK_ID = "windows-server-2025-real-boot"
REQUIRED_FILES = (
    "brain_v12/brain/windows_contract_service.py",
    "brain_v12/brain/fetch_windows_execution_contract.py",
    "brain_v12/brain/windows_execution_contract_issuer.py",
    "brain_v12/brain/owner_cryptographic_approval.py",
    "brain_v12/brain/authority_signature.py",
    "tools/windows_contract_control_plane_preflight.py",
    ".github/workflows/brain-windows-real-boot.yml",
)
REQUIRED_WORKFLOW_MARKERS = (
    "windows-real-boot",
    "brain-cloud-executor",
    "BRAIN_AUTHORITY_PUBLIC_KEY_B64_PROTECTED",
    "BRAIN_WINDOWS_CONTROL_PLANE_URL_PROTECTED",
    "BRAIN_WINDOWS_CONTRACT_DELIVERY_KEY_PROTECTED",
    "/dev/kvm",
    "WINDOWS_BOOT_VERIFIED",
)

def gate(root: Path, source_commit: str) -> dict:
    blockers: list[str] = []
    passed: list[str] = []

    if not re.fullmatch(r"[0-9a-f]{40}", source_commit.lower()):
        blockers.append("SOURCE_COMMIT_INVALID")
    else:
        passed.append("SOURCE_COMMIT_FORMAT_VALID")

    missing = [p for p in REQUIRED_FILES if not (root / p).is_file()]
    if missing:
        blockers.append("REQUIRED_FILES_MISSING:" + ",".join(missing))
    else:
        passed.append("WINDOWS_INTEGRATION_FILES_PRESENT")

    workflow = root / ".github/workflows/brain-windows-real-boot.yml"
    if workflow.is_file():
        text = workflow.read_text(encoding="utf-8")
        missing_markers = [m for m in REQUIRED_WORKFLOW_MARKERS if m not in text]
        if missing_markers:
            blockers.append("REAL_BOOT_WORKFLOW_MARKERS_MISSING:" + ",".join(missing_markers))
        else:
            passed.append("REAL_BOOT_WORKFLOW_FAIL_CLOSED_MARKERS_PRESENT")
        if "continue-on-error: true" in text:
            blockers.append("REAL_BOOT_WORKFLOW_CONTINUE_ON_ERROR_FORBIDDEN")
        else:
            passed.append("REAL_BOOT_WORKFLOW_NO_CONTINUE_ON_ERROR")
        if "WINDOWS_BOOT_VERIFIED" not in text:
            blockers.append("GUEST_BOOT_EVIDENCE_REQUIRED")
    else:
        blockers.append("REAL_BOOT_WORKFLOW_REQUIRED")

    integration = root / ".github/workflows/brain-windows-integration-gate.yml"
    if integration.is_file():
        text = integration.read_text(encoding="utf-8")
        if "windows_contract_control_plane_preflight.py" not in text:
            blockers.append("INTEGRATION_GATE_MISSING_CONTROL_PLANE_PREFLIGHT")
        else:
            passed.append("CONTROL_PLANE_PREFLIGHT_WIRED")
        if "test_windows_contract_issuer_replay_integration" not in text:
            blockers.append("INTEGRATION_GATE_MISSING_REPLAY_TEST")
        else:
            passed.append("OWNER_APPROVAL_REPLAY_TEST_WIRED")
    else:
        blockers.append("INTEGRATION_GATE_WORKFLOW_REQUIRED")

    return {
        "ok": not blockers,
        "status": "READY_FOR_WINDOWS_INTEGRATION_TESTS" if not blockers else "BLOCKED",
        "task_id": TASK_ID,
        "source_commit": source_commit.lower(),
        "passed": passed,
        "blockers": blockers,
        "real_windows_boot_verified": False,
        "contract_issued": False,
        "system_state_changed": False,
    }

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    report = gate(Path(args.root).resolve(), args.source_commit)
    print(json.dumps(report, sort_keys=True))
    return 0 if report["ok"] else 2

if __name__ == "__main__":
    raise SystemExit(main())
