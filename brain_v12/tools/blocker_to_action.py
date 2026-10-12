"""Classify Brain blockers and return one bounded, evidence-based next action.

This module is diagnostic only: it does not create secrets, change permissions,
provision infrastructure, execute shell commands, or bypass completion gates.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

CATALOG: dict[str, dict[str, str]] = {
    "CLOUD_WINDOWS_PROVIDER_NOT_CONFIGURED": {
        "category": "provider",
        "action": "Configure an explicitly approved provider adapter, then rerun provider readiness.",
        "owner": "operator",
    },
    "BRAIN_CLOUD_EXECUTOR_REGISTRY_URL_PROTECTED_MISSING": {
        "category": "configuration",
        "action": "Add the registry URL to the protected environment under the exact required name; rerun readiness.",
        "owner": "repository_admin",
    },
    "API_PERMISSION_DENIED": {
        "category": "authorization",
        "action": "Check token type, repository scope, and read-only runner-administration permission; never print token values.",
        "owner": "repository_admin",
    },
    "WINDOWS_EXECUTION_CONTRACT_FILE_REQUIRED": {
        "category": "execution_contract",
        "action": "Issue and securely stage a signed, unexpired contract bound to the exact task, attempt, and source commit.",
        "owner": "control_plane",
    },
    "LINUX_X64_REQUIRED": {
        "category": "runner",
        "action": "Route to a trusted Linux x86_64 runner; do not emulate a missing capability as PASS.",
        "owner": "runner_admin",
    },
    "KVM_UNAVAILABLE": {
        "category": "runner",
        "action": "Use a trusted runner with /dev/kvm access and verify that the runner job can actually use it.",
        "owner": "runner_admin",
    },
    "WINDOWS_ADMIN_SECRET_MISSING": {
        "category": "secrets",
        "action": "Create the required administrator secrets through an authorized GitHub secret-write path; never place values in logs.",
        "owner": "repository_admin",
    },
    "RUNNER_EXECUTION_PROBE_NOT_PASS": {
        "category": "runner",
        "action": "Keep runner health NOT_VERIFIED and run the explicit execution probe on a runner with required labels.",
        "owner": "runner_admin",
    },
    "WINDOWS_GUEST_NOT_VERIFIED": {
        "category": "completion",
        "action": "Require Azure VM running state, reachable WinRM HTTPS, and authenticated guest OS evidence.",
        "owner": "verification_gate",
    },
    "UNKNOWN_BLOCKER": {
        "category": "unknown",
        "action": "Collect sanitized logs and add a tested mapping before attempting an automated repair.",
        "owner": "brain",
    },
}


def classify(report: dict[str, Any]) -> dict[str, Any]:
    """Return a stable blocker classification and an explicit next action."""
    raw = str(report.get("blocker_code") or report.get("reason") or "UNKNOWN_BLOCKER")
    code = raw.strip().upper()
    # Map known legacy labels to stable blocker codes.
    aliases = {
        "CLOUD_WINDOWS_PROVIDER_NOT_CONFIGURED": "CLOUD_WINDOWS_PROVIDER_NOT_CONFIGURED",
        "CLOUD_WINDOWS_PROVIDER_MISSING": "CLOUD_WINDOWS_PROVIDER_NOT_CONFIGURED",
        "BRAIN_CLOUD_EXECUTOR_REGISTRY_URL_PROTECTED_IS_MISSING": "BRAIN_CLOUD_EXECUTOR_REGISTRY_URL_PROTECTED_MISSING",
        "WINDOWS_ADMIN_USERNAME_OR_PASSWORD_MISSING": "WINDOWS_ADMIN_SECRET_MISSING",
        "WINDOWS_BOOT_NOT_VERIFIED": "WINDOWS_GUEST_NOT_VERIFIED",
    }
    code = aliases.get(code, code)
    item = CATALOG.get(code, CATALOG["UNKNOWN_BLOCKER"])
    fingerprint = hashlib.sha256(
        json.dumps({"code": code, "category": item["category"]}, sort_keys=True).encode()
    ).hexdigest()[:16]
    return {
        "schema_version": 1,
        "status": "BLOCKED" if code != "UNKNOWN_BLOCKER" else "NEEDS_DIAGNOSIS",
        "blocker_code": code if code in CATALOG else "UNKNOWN_BLOCKER",
        "fingerprint": fingerprint,
        "category": item["category"],
        "next_action": item["action"],
        "owner": item["owner"],
        "retry_policy": "DO_NOT_REPEAT_IDENTICAL_ACTION_WITHOUT_NEW_EVIDENCE",
        "evidence_received": bool(report.get("evidence") or report.get("run_url") or report.get("observed_at")),
        "secrets_logged": False,
        "source_mutation": "NONE",
    }


def classify_many(reports: list[dict[str, Any]]) -> dict[str, Any]:
    results = [classify(item if isinstance(item, dict) else {}) for item in reports]
    # Preserve input order while collapsing duplicate blockers by fingerprint.
    unique = []
    seen = set()
    for result in results:
        if result["fingerprint"] not in seen:
            unique.append(result)
            seen.add(result["fingerprint"])
    return {"schema_version": 1, "blocker_count": len(unique), "blockers": unique}
