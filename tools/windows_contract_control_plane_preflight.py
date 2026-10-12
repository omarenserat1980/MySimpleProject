#!/usr/bin/env python3
"""Read-only readiness gate for issuing a real Windows boot execution contract.

Run on the Brain Control Plane host immediately before authorizing a workflow
attempt. Never prints secret material and never issues/consumes an approval.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

# Allow direct execution from the repository root or another working directory.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

TASK_ID = "windows-server-2025-real-boot"
SCOPE = "windows-server-2025-real-boot"


def _json_file(path: str, code: str) -> dict:
    p = Path(path)
    if not p.is_file():
        raise RuntimeError(code)
    try:
        value = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise RuntimeError(code) from None
    if not isinstance(value, dict):
        raise RuntimeError(code)
    return value


def _key_present(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise RuntimeError(name + "_REQUIRED")
    return value


def check(args) -> dict:
    blockers: list[str] = []
    passed: list[str] = []

    if not re.fullmatch(r"[0-9a-f]{40}", args.source_commit.lower()):
        blockers.append("SOURCE_COMMIT_INVALID")
    if args.task_id != TASK_ID:
        blockers.append("TASK_SCOPE_MISMATCH")
    if not args.attempt_id or not re.fullmatch(r"github-[0-9]+-attempt-[0-9]+", args.attempt_id):
        blockers.append("ATTEMPT_ID_INVALID")

    env_values = {}
    for name in (
        "BRAIN_AUTHORITY_PRIVATE_KEY_B64",
        "BRAIN_OWNER_APPROVAL_PUBLIC_KEY_B64",
        "BRAIN_HUMAN_APPROVAL_TOKEN",
    ):
        try:
            env_values[name] = _key_present(name)
        except RuntimeError as exc:
            blockers.append(str(exc))

    for name in ("BRAIN_AUTHORITY_PRIVATE_KEY_B64", "BRAIN_OWNER_APPROVAL_PUBLIC_KEY_B64"):
        value = env_values.get(name)
        if value:
            try:
                decoded = base64.b64decode(value, validate=True)
                if len(decoded) != 32:
                    raise ValueError()
                passed.append(name + "_FORMAT_VALID")
            except (ValueError, TypeError):
                blockers.append(name + "_FORMAT_INVALID")

    identity = checkpoint = lease_data = approval = None
    try:
        identity = _json_file(args.identity_file, "BRAIN_IDENTITY_FILE_REQUIRED")
        checkpoint = _json_file(args.checkpoint_file, "BRAIN_CHECKPOINT_FILE_REQUIRED")
        from brain_v12.brain.brain_identity import require_checkpoint_identity
        require_checkpoint_identity(identity, checkpoint)
        passed.append("IDENTITY_CHECKPOINT_VALID")
    except (RuntimeError, ValueError) as exc:
        blockers.append(str(exc).splitlines()[0][:120])

    try:
        lease_data = _json_file(args.lease_file, "BRAIN_LEADERSHIP_LEASE_FILE_REQUIRED")
        for field in ("brain_id", "generation", "lease_id", "fencing_token", "holder_id", "acquired_at", "expires_at"):
            if field not in lease_data:
                raise RuntimeError("BRAIN_LEADERSHIP_LEASE_INVALID")
        if int(lease_data["fencing_token"]) < 1 or not str(lease_data["holder_id"]).strip():
            raise RuntimeError("BRAIN_LEADERSHIP_LEASE_INVALID")
        if float(lease_data["expires_at"]) <= time.time() + 60:
            raise RuntimeError("BRAIN_LEADERSHIP_LEASE_EXPIRY_TOO_SOON")
        db = Path(args.leadership_db)
        if not db.is_file():
            raise RuntimeError("BRAIN_LEADERSHIP_STORE_REQUIRED")
        uri = "file:" + str(db.resolve()) + "?mode=ro"
        with sqlite3.connect(uri, uri=True, timeout=3) as conn:
            row = conn.execute(
                "SELECT brain_id,generation,lease_id,fencing_token,holder_id,acquired_at,expires_at "
                "FROM leadership WHERE singleton=1"
            ).fetchone()
        expected = tuple(lease_data[k] for k in (
            "brain_id", "generation", "lease_id", "fencing_token", "holder_id", "acquired_at", "expires_at"
        ))
        if row is None or tuple(row) != expected or float(row[6]) <= time.time() + 60:
            raise RuntimeError("BRAIN_LEADERSHIP_LEASE_NOT_CURRENT")
        passed.append("LEADERSHIP_LEASE_CURRENT")
    except (RuntimeError, OSError, ValueError, TypeError, sqlite3.Error) as exc:
        blockers.append(str(exc).splitlines()[0][:120])

    try:
        approval = _json_file(args.owner_approval_file, "OWNER_APPROVAL_FILE_REQUIRED")
        public_key = env_values.get("BRAIN_OWNER_APPROVAL_PUBLIC_KEY_B64", "")
        if not public_key:
            raise RuntimeError("OWNER_APPROVAL_PUBLIC_KEY_REQUIRED")
        from brain_v12.brain.owner_cryptographic_approval import verify_owner_approval
        owner = verify_owner_approval(
            approval, public_key, source_commit=args.source_commit.lower(),
            task_id=args.task_id, attempt_id=args.attempt_id,
        )
        # Read the one-time challenge ledger without mutating it.
        db = Path(args.leadership_db)
        uri = "file:" + str(db.resolve()) + "?mode=ro"
        with sqlite3.connect(uri, uri=True, timeout=3) as conn:
            table = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='consumed_owner_approvals'"
            ).fetchone()
            if table and conn.execute(
                "SELECT 1 FROM consumed_owner_approvals WHERE challenge_id=?",
                (owner.challenge_id,),
            ).fetchone():
                raise RuntimeError("OWNER_APPROVAL_ALREADY_CONSUMED")
        if owner.scope != SCOPE:
            raise RuntimeError("OWNER_APPROVAL_SCOPE_MISMATCH")
        if owner.expires_at <= time.time() + 60:
            raise RuntimeError("OWNER_APPROVAL_EXPIRY_TOO_SOON")
        passed.append("OWNER_APPROVAL_VALID_FOR_EXACT_ATTEMPT")
    except (RuntimeError, ValueError, TypeError) as exc:
        blockers.append(str(exc).splitlines()[0][:120])

    return {
        "ok": not blockers,
        "status": "READY_FOR_AUTHORIZED_ISSUANCE" if not blockers else "BLOCKED",
        "source_commit": args.source_commit.lower() if re.fullmatch(r"[0-9a-f]{40}", args.source_commit.lower()) else "INVALID",
        "task_id": args.task_id,
        "attempt_id": args.attempt_id,
        "passed": sorted(set(passed)),
        "blockers": sorted(set(blockers)),
        "contract_issued": False,
        "owner_approval_consumed": False,
        "system_state_changed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--task-id", default=TASK_ID)
    parser.add_argument("--attempt-id", required=True)
    parser.add_argument("--identity-file", default=os.getenv("BRAIN_IDENTITY_FILE", "/etc/brain/identity.json"))
    parser.add_argument("--checkpoint-file", default=os.getenv("BRAIN_CHECKPOINT_FILE", "/etc/brain/checkpoint.json"))
    parser.add_argument("--lease-file", default=os.getenv("BRAIN_LEADERSHIP_LEASE_FILE", "/etc/brain/leadership-lease.json"))
    parser.add_argument("--owner-approval-file", default=os.getenv("BRAIN_OWNER_APPROVAL_FILE", "/etc/brain/owner-approval.json"))
    parser.add_argument("--leadership-db", default=os.getenv("BRAIN_LEADERSHIP_DB", "brain6_artifacts/control_plane/leadership.db"))
    args = parser.parse_args()
    try:
        report = check(args)
    except Exception:
        report = {
            "ok": False, "status": "BLOCKED", "blockers": ["PREFLIGHT_INTERNAL_ERROR"],
            "contract_issued": False, "owner_approval_consumed": False,
            "system_state_changed": False,
        }
    print(json.dumps(report, sort_keys=True))
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
