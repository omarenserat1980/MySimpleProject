"""Fail-closed direct action executor for a Brain cloud worker.

The worker executes a small allowlisted action set only after verifying a
short-lived, Brain-signed execution contract and executor attestation.
It never exposes a general shell and never claims Windows boot success.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import time
from pathlib import Path
from typing import Any

from .authority_signature import verify_contract_signature
from .cloud_executor_attestation import verify_from_environment

ALLOWED_ACTIONS = {
    "integration_gate": ["python3", "tools/brain_windows_integration_gate.py"],
    "cloud_executor_gate": ["python3", "brain_v12/brain/cloud_executor_gate.py"],
    "kvm_probe": ["python3", "brain_v12/brain/cloud_executor_gate.py"],
}
REQUIRED_CAPABILITY = "windows-server-2025-real-boot"
REQUIRED_EXECUTOR = "windows-real-boot-qemu"


def _load(path: str) -> dict[str, Any]:
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError("ACTION_CONTRACT_INVALID")
    return data


def _verify_contract(contract: dict[str, Any], source_commit: str, action: str) -> None:
    if contract.get("status") != "VERIFIED":
        raise RuntimeError("ACTION_CONTRACT_NOT_VERIFIED")
    if contract.get("capability") != REQUIRED_CAPABILITY:
        raise RuntimeError("ACTION_CONTRACT_CAPABILITY_MISMATCH")
    if contract.get("executor") != REQUIRED_EXECUTOR:
        raise RuntimeError("ACTION_CONTRACT_EXECUTOR_MISMATCH")
    if contract.get("source_commit") != source_commit.lower():
        raise RuntimeError("ACTION_CONTRACT_SOURCE_COMMIT_MISMATCH")
    if contract.get("task_id") != REQUIRED_CAPABILITY:
        raise RuntimeError("ACTION_CONTRACT_TASK_SCOPE_MISMATCH")
    if contract.get("expires_at", 0) <= time.time():
        raise RuntimeError("ACTION_CONTRACT_EXPIRED")
    if action not in ALLOWED_ACTIONS:
        raise RuntimeError("ACTION_NOT_ALLOWLISTED")
    public_key = os.environ.get("BRAIN_AUTHORITY_PUBLIC_KEY_B64", "")
    if not public_key or not verify_contract_signature(
        contract, str(contract.get("authority_signature", "")), public_key
    ):
        raise RuntimeError("ACTION_CONTRACT_SIGNATURE_INVALID")


def execute(contract: dict[str, Any], *, action: str, source_commit: str, root: str = ".") -> dict[str, Any]:
    _verify_contract(contract, source_commit, action)
    executor_id = os.environ.get("BRAIN_CLOUD_EXECUTOR_ID", "").strip()
    if os.environ.get("BRAIN_CLOUD_EXECUTOR") != "1" or not executor_id:
        raise RuntimeError("CLOUD_EXECUTOR_IDENTITY_REQUIRED")
    try:
        attestation = verify_from_environment(executor_id)
    except (ValueError, OSError) as exc:
        raise RuntimeError(str(exc)) from exc

    command = list(ALLOWED_ACTIONS[action])
    if action == "integration_gate":
        command += ["--source-commit", source_commit]
    elif action == "cloud_executor_gate":
        command += ["--output", "cloud-direct-executor-gate.json"]

    started = time.time()
    try:
        proc = subprocess.run(
            command,
            cwd=str(Path(root).resolve()),
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("DIRECT_ACTION_TIMEOUT") from exc
    finished = time.time()
    stdout = (proc.stdout or "")[-4000:]
    stderr = (proc.stderr or "")[-4000:]
    evidence = {
        "schema": "brain.cloud-direct-action-evidence.v1",
        "verified": proc.returncode == 0,
        "action": action,
        "executor_id": executor_id,
        "source_commit": source_commit.lower(),
        "contract_id": hashlib.sha256(
            json.dumps(contract, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "started_at": started,
        "finished_at": finished,
        "return_code": proc.returncode,
        "platform": platform.machine(),
        "attestation_expires_at": attestation["expires_at"],
        "stdout_tail": stdout,
        "stderr_tail": stderr,
        "rule": "signed short-lived contract + verified executor attestation + allowlisted action",
    }
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True)
    parser.add_argument("--action", choices=sorted(ALLOWED_ACTIONS), required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--root", default=".")
    parser.add_argument("--output", default="cloud-direct-action-evidence.json")
    args = parser.parse_args()
    try:
        evidence = execute(
            _load(args.contract),
            action=args.action,
            source_commit=args.source_commit,
            root=args.root,
        )
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        evidence = {
            "schema": "brain.cloud-direct-action-evidence.v1",
            "verified": False,
            "action": args.action,
            "source_commit": args.source_commit.lower(),
            "error": str(exc),
        }
        Path(args.output).write_text(json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps(evidence, sort_keys=True))
        return 2
    Path(args.output).write_text(json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(evidence, sort_keys=True))
    return 0 if evidence["verified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
