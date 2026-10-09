"""Closed-loop Windows Server 2025 execution contract gate.

The workflow may prove QEMU/Windows boot, but it may not self-authorize.
A Brain-owned cloud executor must provide a pre-issued execution contract.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any

SHA40 = re.compile(r"^[0-9a-f]{40}$")


def load_and_verify(path: str | Path | None = None, *, now: float | None = None) -> dict[str, Any]:
    contract_path = Path(path or os.environ.get(
        "BRAIN_WINDOWS_EXECUTION_CONTRACT_FILE",
        "/etc/brain/windows-execution-contract.json",
    ))
    if not contract_path.is_file():
        raise RuntimeError("WINDOWS_EXECUTION_CONTRACT_FILE_REQUIRED")

    try:
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"WINDOWS_EXECUTION_CONTRACT_INVALID_JSON:{type(exc).__name__}") from exc

    if contract.get("schema") != "brain.windows-execution-contract.v1":
        raise RuntimeError("WINDOWS_EXECUTION_CONTRACT_SCHEMA_INVALID")
    if contract.get("status") != "VERIFIED":
        raise RuntimeError("WINDOWS_EXECUTION_CONTRACT_NOT_VERIFIED")
    if contract.get("capability") != "windows-server-2025-real-boot":
        raise RuntimeError("WINDOWS_EXECUTION_CONTRACT_CAPABILITY_INVALID")
    if contract.get("executor") != "windows-real-boot-qemu":
        raise RuntimeError("WINDOWS_EXECUTION_CONTRACT_EXECUTOR_INVALID")
    if contract.get("authority_policy_version") != "authority-policy-v1":
        raise RuntimeError("WINDOWS_EXECUTION_CONTRACT_AUTHORITY_POLICY_INVALID")
    if contract.get("authority_decision") != "AUTHORIZED":
        raise RuntimeError("WINDOWS_EXECUTION_CONTRACT_AUTHORITY_NOT_AUTHORIZED")
    if not str(contract.get("owner_id", "")).strip():
        raise RuntimeError("WINDOWS_EXECUTION_CONTRACT_OWNER_ID_REQUIRED")
    if not str(contract.get("owner_challenge_id", "")).strip():
        raise RuntimeError("WINDOWS_EXECUTION_CONTRACT_OWNER_CHALLENGE_REQUIRED")
    if contract.get("owner_scope") != "windows-server-2025-real-boot":
        raise RuntimeError("WINDOWS_EXECUTION_CONTRACT_OWNER_SCOPE_INVALID")

    signature = str(contract.get("authority_signature", "")).strip()
    if not signature:
        raise RuntimeError("WINDOWS_EXECUTION_CONTRACT_AUTHORITY_SIGNATURE_REQUIRED")
    from brain_v12.brain.authority_signature import verify_contract_signature
    if not verify_contract_signature(contract, signature):
        raise RuntimeError("WINDOWS_EXECUTION_CONTRACT_AUTHORITY_SIGNATURE_INVALID")

    brain_id = str(contract.get("brain_id", "")).strip()
    if not brain_id:
        raise RuntimeError("WINDOWS_EXECUTION_CONTRACT_BRAIN_ID_REQUIRED")

    generation = contract.get("generation")
    token = contract.get("fencing_token")
    if not isinstance(generation, int) or isinstance(generation, bool) or generation < 1:
        raise RuntimeError("WINDOWS_EXECUTION_CONTRACT_GENERATION_INVALID")
    if not isinstance(token, int) or isinstance(token, bool) or token < 1:
        raise RuntimeError("WINDOWS_EXECUTION_CONTRACT_FENCING_TOKEN_REQUIRED")

    for field in ("lease_id", "holder_id", "task_id", "attempt_id"):
        if not str(contract.get(field, "")).strip():
            raise RuntimeError(f"WINDOWS_EXECUTION_CONTRACT_{field.upper()}_REQUIRED")

    source_commit = str(contract.get("source_commit", ""))
    if not SHA40.fullmatch(source_commit):
        raise RuntimeError("WINDOWS_EXECUTION_CONTRACT_SOURCE_COMMIT_INVALID")

    github_sha = str(os.environ.get("GITHUB_SHA", "")).strip().lower()
    if github_sha and SHA40.fullmatch(github_sha) and source_commit != github_sha:
        raise RuntimeError("WINDOWS_EXECUTION_CONTRACT_SOURCE_COMMIT_MISMATCH")

    expires_at = contract.get("expires_at")
    try:
        expires_at = float(expires_at)
    except (TypeError, ValueError) as exc:
        raise RuntimeError("WINDOWS_EXECUTION_CONTRACT_EXPIRY_INVALID") from exc

    now_value = time.time() if now is None else float(now)
    if expires_at <= now_value:
        raise RuntimeError("WINDOWS_EXECUTION_CONTRACT_EXPIRED")

    raw = json.dumps(contract, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    digest = hashlib.sha256(raw).hexdigest()
    return {
        "verified": True,
        "contract_sha256": digest,
        "contract": contract,
        "evidence_ref": f"windows-execution-contract:{contract.get('attempt_id')}",
    }


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--path")
    p.add_argument("--output", default="windows-execution-contract-gate.json")
    args = p.parse_args()
    result = load_and_verify(args.path)
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    print("WINDOWS_EXECUTION_CONTRACT=VERIFIED")
