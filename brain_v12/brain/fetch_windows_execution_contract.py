"""Fetch a short-lived signed Windows execution contract over HTTPS."""
from __future__ import annotations

import json
import os
import pathlib
import re
import sys
import tempfile
import urllib.error
import urllib.request


def main() -> int:
    base = os.environ.get("BRAIN_WINDOWS_CONTROL_PLANE_URL", "").strip().rstrip("/")
    key = os.environ.get("BRAIN_WINDOWS_CONTRACT_DELIVERY_KEY", "")
    commit = os.environ.get("GITHUB_SHA", "").strip().lower()
    run_id = os.environ.get("GITHUB_RUN_ID", "").strip()
    run_attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "").strip()
    if not base or not key:
        raise RuntimeError("BRAIN_WINDOWS_CONTRACT_DELIVERY_CONFIG_REQUIRED")
    if not base.startswith("https://"):
        raise RuntimeError("BRAIN_WINDOWS_CONTROL_PLANE_HTTPS_REQUIRED")
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise RuntimeError("GITHUB_SHA_INVALID")
    if not run_id.isdigit() or not run_attempt.isdigit():
        raise RuntimeError("GITHUB_RUN_ID_OR_ATTEMPT_INVALID")

    expected = {
        "source_commit": commit,
        "task_id": "windows-server-2025-real-boot",
        "attempt_id": f"github-{run_id}-attempt-{run_attempt}",
    }
    req = urllib.request.Request(
        base + "/api/brain/windows/contracts/issue",
        data=json.dumps(expected).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Brain-Contract-Delivery-Key": key,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            if response.status != 200:
                raise RuntimeError("BRAIN_CONTRACT_ISSUANCE_HTTP_STATUS")
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"BRAIN_CONTRACT_ISSUANCE_HTTP_{exc.code}") from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise RuntimeError("BRAIN_CONTRACT_CONTROL_PLANE_UNREACHABLE") from None

    contract = payload.get("contract")
    if payload.get("issued") is not True or not isinstance(contract, dict):
        raise RuntimeError("BRAIN_CONTRACT_RESPONSE_INVALID")
    if any(contract.get(field) != value for field, value in expected.items()):
        raise RuntimeError("BRAIN_CONTRACT_RESPONSE_BINDING_MISMATCH")
    if not contract.get("authority_signature") or not contract.get("expires_at"):
        raise RuntimeError("BRAIN_CONTRACT_SIGNATURE_OR_EXPIRY_MISSING")

    # Verify the authority signature with the public key available to the executor.
    # The verifier takes both the complete contract and its detached signature.
    from brain_v12.brain.authority_signature import verify_contract_signature
    if not verify_contract_signature(contract, contract.get("authority_signature")):
        raise RuntimeError("BRAIN_CONTRACT_AUTHORITY_SIGNATURE_INVALID")
    try:
        expires_at = float(contract["expires_at"])
    except (TypeError, ValueError) as exc:
        raise RuntimeError("BRAIN_CONTRACT_EXPIRY_INVALID") from exc
    import math
    import time
    if not math.isfinite(expires_at) or expires_at <= time.time():
        raise RuntimeError("BRAIN_CONTRACT_EXPIRED")

    destination = pathlib.Path(os.environ.get(
        "BRAIN_WINDOWS_EXECUTION_CONTRACT_FILE",
        "/run/brain/windows-execution-contract.json",
    ))
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(
        prefix=destination.name + ".", suffix=".tmp", dir=str(destination.parent)
    )
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(contract, stream, sort_keys=True, separators=(",", ":"))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass

    print("BRAIN_CONTRACT_FETCHED=1")
    print("BRAIN_CONTRACT_SOURCE_COMMIT=" + commit)
    print("BRAIN_CONTRACT_ATTEMPT=" + expected["attempt_id"])
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print("BRAIN_CONTRACT_FETCH_FAILED=" + str(exc), file=sys.stderr)
        raise SystemExit(2)
