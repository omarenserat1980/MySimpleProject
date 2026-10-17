"""One-shot cloud executor bootstrap and live attestation probe.

Run on the intended worker host with host-provisioned environment variables.
This script proves only that the configured host completed the signed attestation
round trip; it does not prove ASIC hardware or mining activity.
"""
from __future__ import annotations

import json
import os
import platform
import socket
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from brain_v12.brain.cloud_executor_attestation import verify_from_environment


def _post_json(base_url: str, path: str, token: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        base_url.rstrip("/") + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Brain-Executor-Token": token,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("CLOUD_EXECUTOR_ATTESTATION_REQUEST_FAILED") from exc
    if not isinstance(result, dict):
        raise RuntimeError("CLOUD_EXECUTOR_ATTESTATION_RESPONSE_INVALID")
    return result


def run_probe() -> dict[str, Any]:
    base_url = os.environ.get("BRAIN_CLOUD_EXECUTOR_REGISTRY_URL", "").rstrip("/")
    token = os.environ.get("BRAIN_CLOUD_EXECUTOR_TOKEN", "")
    executor_id = os.environ.get("BRAIN_CLOUD_EXECUTOR_ID", "").strip()
    public_key = os.environ.get("BRAIN_CLOUD_EXECUTOR_ATTESTATION_PUBLIC_KEY_B64", "")
    if not base_url.startswith("https://"):
        raise RuntimeError("CLOUD_EXECUTOR_REGISTRY_HTTPS_REQUIRED")
    if not token or not executor_id or not public_key:
        raise RuntimeError("CLOUD_EXECUTOR_REQUIRED_ENVIRONMENT_MISSING")

    actual_arch = platform.machine().lower()
    actual_arch = "x86_64" if actual_arch in {"x86_64", "amd64"} else actual_arch
    if actual_arch != "x86_64":
        raise RuntimeError("CLOUD_EXECUTOR_UNSUPPORTED_ARCHITECTURE")

    challenge = _post_json(
        base_url, "/api/cloud-executor/attestation/challenge", token,
        {"executor_id": executor_id},
    )
    nonce = challenge.get("nonce")
    if not isinstance(nonce, str) or len(nonce) < 32:
        raise RuntimeError("CLOUD_EXECUTOR_CHALLENGE_INVALID")

    attestation = _post_json(
        base_url, "/api/cloud-executor/attestation/issue", token,
        {"executor_id": executor_id, "nonce": nonce},
    )
    if attestation.get("executor_id") != executor_id or attestation.get("nonce") != nonce:
        raise RuntimeError("CLOUD_EXECUTOR_ATTESTATION_BINDING_MISMATCH")

    fd, filename = tempfile.mkstemp(prefix="brain-cloud-attestation-", suffix=".json")
    path = Path(filename)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(attestation, stream, separators=(",", ":"), sort_keys=True)
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
        os.environ["BRAIN_CLOUD_EXECUTOR_ATTESTATION_FILE"] = str(path)
        # Verifies signature, expiry, executor, actual hostname/architecture,
        # then consumes the nonce once in the central registry over HTTPS.
        verified = verify_from_environment(executor_id)
        return {
            "ok": True,
            "status": "LIVE_ATTESTATION_VERIFIED",
            "executor_id": verified["executor_id"],
            "hostname": verified["hostname"],
            "architecture": verified["architecture"],
            "issued_at": verified["issued_at"],
            "expires_at": verified["expires_at"],
            "central_nonce_consumed": True,
            "evidence_note": (
                "Signed live attestation round trip succeeded on this host. "
                "This is not proof of ASIC hardware or mining revenue."
            ),
        }
    finally:
        try:
            path.unlink()
        except OSError:
            pass


def main() -> int:
    try:
        result = run_probe()
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception as exc:
        # Emit stable error codes only; never print environment variables or tokens.
        code = str(exc) if str(exc).startswith("CLOUD_EXECUTOR_") else "CLOUD_EXECUTOR_PROBE_FAILED"
        print(json.dumps({"ok": False, "status": "UNVERIFIED", "error": code}, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
