"""Secret-safe, read-only readiness checks for Windows contract issuance."""
from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any

SECRET_ENV_NAMES = (
    "BRAIN_WINDOWS_CONTRACT_DELIVERY_KEY",
    "BRAIN_AUTHORITY_PRIVATE_KEY_B64",
    "BRAIN_OWNER_APPROVAL_PUBLIC_KEY_B64",
    "BRAIN_HUMAN_APPROVAL_TOKEN",
)
FILE_ENV_DEFAULTS = {
    "identity": ("BRAIN_IDENTITY_FILE", "/etc/brain/identity.json"),
    "checkpoint": ("BRAIN_CHECKPOINT_FILE", "/etc/brain/checkpoint.json"),
    "leadership_lease": ("BRAIN_LEADERSHIP_LEASE_FILE", "/etc/brain/leadership-lease.json"),
    "owner_approval": ("BRAIN_OWNER_APPROVAL_FILE", "/etc/brain/owner-approval.json"),
}

def _json_file_status(path_text: str) -> dict[str, Any]:
    path = Path(path_text)
    if not path.is_file():
        return {"present": False, "readable_json_object": False, "reason": "FILE_MISSING"}
    try:
        with path.open("r", encoding="utf-8") as stream:
            value = json.load(stream)
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {"present": True, "readable_json_object": False, "reason": "FILE_UNREADABLE_OR_INVALID"}
    if not isinstance(value, dict):
        return {"present": True, "readable_json_object": False, "reason": "JSON_ROOT_NOT_OBJECT"}
    return {"present": True, "readable_json_object": True, "reason": "OK"}

def readiness_snapshot(environ: dict[str, str] | None = None) -> dict[str, Any]:
    """Return presence-only checks; never issue or consume authorization."""
    env = os.environ if environ is None else environ
    secrets = {name: bool(str(env.get(name, "")).strip()) for name in SECRET_ENV_NAMES}
    files: dict[str, Any] = {}
    for label, (env_name, default_path) in FILE_ENV_DEFAULTS.items():
        path = str(env.get(env_name, default_path)).strip()
        if not path:
            files[label] = {"configured": False, "present": False,
                            "readable_json_object": False, "reason": "PATH_NOT_CONFIGURED"}
        else:
            files[label] = {"configured": True, **_json_file_status(path)}
    checks = {
        "delivery_auth_configured": secrets["BRAIN_WINDOWS_CONTRACT_DELIVERY_KEY"],
        "authority_signing_key_configured": secrets["BRAIN_AUTHORITY_PRIVATE_KEY_B64"],
        "owner_approval_verification_key_configured": secrets["BRAIN_OWNER_APPROVAL_PUBLIC_KEY_B64"],
        "human_approval_token_configured": secrets["BRAIN_HUMAN_APPROVAL_TOKEN"],
        "required_files_readable": all(x["readable_json_object"] for x in files.values()),
    }
    ok = all(checks.values())
    return {
        "ok": ok,
        "status": "READY_FOR_ATTEMPT_BOUND_ISSUANCE" if ok else "BLOCKED",
        "scope": "read-only-presence-and-file-format-check; does-not-issue-contract",
        "secrets": secrets,
        "files": files,
        "checks": checks,
        "next": "Use a fresh workflow attempt to verify approval binding, current lease, authority policy, signature, and expiry.",
    }
