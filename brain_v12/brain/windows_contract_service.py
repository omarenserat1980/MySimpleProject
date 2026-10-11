"""Brain Control Plane service for issuing short-lived Windows real-boot contracts.

Important topology rule:
The Control Plane authorizes a run; the dedicated GitHub self-hosted executor
proves its local QEMU/KVM capability in the workflow before requesting this
contract. The Control Plane may run on a different host and must not require
its own /dev/kvm, QEMU, or OVMF installation.

The capability probe below is diagnostic only. Runtime capability is enforced
by the runner-side cloud_executor_gate.py and internal_runner_preflight.py.
"""
from __future__ import annotations

import os
import platform
import shutil
import time
from pathlib import Path
from typing import Any

from .windows_execution_contract_issuer import issue_from_files


def capability_probe() -> dict[str, Any]:
    """Describe local host capability for diagnostics; never gate issuance on it."""
    checks = {
        "arch": platform.machine().lower() in {"x86_64", "amd64"},
        "qemu": bool(shutil.which("qemu-system-x86_64")),
        "qemu_img": bool(shutil.which("qemu-img")),
        "kvm": Path("/dev/kvm").exists(),
        "ovmf": Path(os.getenv("BRAIN_OVMF_CODE", "/usr/share/OVMF/OVMF_CODE_4M.fd")).is_file(),
    }
    return {
        "verified": all(checks.values()),
        "scope": "control-plane-host-diagnostic-only",
        "checks": checks,
    }


def issue(request: dict[str, Any]) -> dict[str, Any]:
    """Issue an owner-authorized contract after the runner-side capability gate.

    The delivery endpoint is called by the dedicated workflow only after its
    executor preflight has passed. This host-side function deliberately does
    not infer executor capability from the Control Plane machine.
    """
    required = ("source_commit", "task_id", "attempt_id")
    for key in required:
        if not str(request.get(key, "")).strip():
            raise RuntimeError("WINDOWS_CONTRACT_REQUEST_" + key.upper() + "_REQUIRED")

    identity = os.environ.get("BRAIN_IDENTITY_FILE", "/etc/brain/identity.json")
    checkpoint = os.environ.get("BRAIN_CHECKPOINT_FILE", "/etc/brain/checkpoint.json")
    lease = os.environ.get("BRAIN_LEADERSHIP_LEASE_FILE", "/etc/brain/leadership-lease.json")
    owner_approval = os.environ.get("BRAIN_OWNER_APPROVAL_FILE", "/etc/brain/owner-approval.json")
    owner_public_key = os.environ.get("BRAIN_OWNER_APPROVAL_PUBLIC_KEY_B64", "")
    output = os.environ.get("BRAIN_WINDOWS_CONTRACT_OUTPUT", "/run/brain/windows-execution-contract.json")

    # This records owner authorization only; it is NOT evidence that this
    # Control Plane host can run QEMU/KVM. The executor enforces QEMU/KVM
    # capability independently before and during the workflow.
    result = issue_from_files(
        identity_file=identity,
        checkpoint_file=checkpoint,
        lease_file=lease,
        output=output,
        source_commit=str(request["source_commit"]).strip().lower(),
        task_id=str(request["task_id"]).strip(),
        attempt_id=str(request["attempt_id"]).strip(),
        capability_verified=True,
        human_approval_token=os.environ.get("BRAIN_HUMAN_APPROVAL_TOKEN"),
        owner_approval_file=owner_approval,
        owner_public_key_b64=owner_public_key,
    )
    return {
        **result,
        "capability": capability_probe(),
        "control_plane": "brain",
        "issued_at": time.time(),
    }
