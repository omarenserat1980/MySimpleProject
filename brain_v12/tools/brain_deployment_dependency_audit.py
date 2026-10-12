"""Secret-safe audit of Brain's deployment endpoint and GitHub runner context.

This is a read-only diagnostic. It never prints endpoint values, credentials, or
secret contents, performs no network requests, and never claims boot success.
"""
from __future__ import annotations

import json
import os
import sys
from urllib.parse import urlsplit


def classify_endpoint(value: str | None) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "MISSING"
    try:
        parsed = urlsplit(raw)
        host = (parsed.hostname or "").lower().rstrip(".")
        if not host or parsed.scheme.lower() not in {"http", "https"}:
            return "INVALID_OR_UNSUPPORTED"
        if parsed.username is not None or parsed.password is not None:
            return "URL_EMBEDS_CREDENTIALS_BLOCKED"
        if host == "render.com" or host.endswith(".render.com"):
            return "LEGACY_RENDER_ENDPOINT"
        if host in {"localhost", "127.0.0.1", "::1"}:
            return "LOCAL_ONLY_ENDPOINT"
        if parsed.scheme.lower() != "https":
            return "HTTPS_REQUIRED"
        return "CONFIGURED_HTTPS_ENDPOINT"
    except (TypeError, ValueError):
        return "INVALID_OR_UNSUPPORTED"


def audit(environ=None) -> dict:
    env = os.environ if environ is None else environ
    endpoints = {
        name: classify_endpoint(env.get(name))
        for name in (
            "BRAIN_WINDOWS_CONTROL_PLANE_URL",
            "BRAIN_URL",
            "V12_BRAIN_URL",
        )
    }
    github_actions = str(env.get("GITHUB_ACTIONS", "")).lower() == "true"
    runner_name_present = bool(str(env.get("RUNNER_NAME", "")).strip())
    internal_flag_present = str(env.get("BRAIN_INTERNAL_RUNNER_FLAG", "")) == "1"
    github_runner_context = github_actions and runner_name_present

    cp = endpoints["BRAIN_WINDOWS_CONTROL_PLANE_URL"]
    blockers = []
    if cp != "CONFIGURED_HTTPS_ENDPOINT":
        blockers.append("CONTROL_PLANE_ENDPOINT_NOT_READY")
    if not github_runner_context:
        blockers.append("GITHUB_ACTIONS_RUNNER_CONTEXT_NOT_PROVEN")
    if not internal_flag_present:
        blockers.append("BRAIN_INTERNAL_RUNNER_FLAG_NOT_PRESENT")

    return {
        "schema_version": 1,
        "status": "BLOCKED" if blockers else "READY_FOR_NEXT_GATE",
        "endpoint_classifications": endpoints,
        "github_actions_runner_context": github_runner_context,
        "runner_name_present": runner_name_present,
        "brain_internal_runner_flag_present": internal_flag_present,
        "blockers": blockers,
        "network_probe_performed": False,
        "secret_values_emitted": False,
        "windows_boot_verified": False,
        "cloud_resources_changed": False,
    }


def main() -> int:
    result = audit()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "READY_FOR_NEXT_GATE" else 2


if __name__ == "__main__":
    sys.exit(main())
