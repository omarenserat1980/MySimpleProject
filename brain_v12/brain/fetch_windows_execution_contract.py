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
    expected = {"source_commit": commit, "task_id": "windows-server-2025-real-boot",
                "attempt_id": f"github-{run_id}-attempt-{run_attempt}"}
    req = urllib.request.Request(
        base + "/api/brain/windows/contracts/issue",
        data=json.dumps(expected).encode(), method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json",
                 "X-Brain-Contract-Delivery-Key": key})
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            if response.status != 200:
                raise RuntimeError("BRAIN_CONTRACT_ISSUANCE_HTTP_STATUS")
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"BRAIN_CONTRACT_ISSUANCE_HTTP_{exc.code}") from None
    except (urllib.error.URLError, TimeoutError):
        raise RuntimeError("BRAIN_CONTRACT_CONTROL_PLANE_UNREACHABLE") from None
    if not isinstance(payload, dict):
        raise RuntimeError("BRAIN_CONTRACT_RESPONSE_INVALID")
    contract = payload.get("contract")
    # Accept either a wrapped Control Plane response or the current service's
    # direct contract object, but validate the same signed binding in both cases.
    if contract is None and payload.get("schema") == "brain.windows-execution-contract.v1":
        contract = payload
    if (payload.get("issued") is not True and contract is not payload) or not isinstance(contract, dict):
        raise RuntimeError("BRAIN_CONTRACT_RESPONSE_INVALID")
    if any(contract.get(k) != v for k, v in expected.items()):
        raise RuntimeError("BRAIN_CONTRACT_RESPONSE_BINDING_MISMATCH")
    if not contract.get("authority_signature") or not contract.get("expires_at"):
        raise RuntimeError("BRAIN_CONTRACT_SIGNATURE_OR_EXPIRY_MISSING")
    from brain_v12.brain.authority_signature import verify_contract_signature
    if not verify_contract_signature(contract):
        raise RuntimeError("BRAIN_CONTRACT_AUTHORITY_SIGNATURE_INVALID")
    try:
        expiry = float(contract["expires_at"])
    except (TypeError, ValueError) as exc:
        raise RuntimeError("BRAIN_CONTRACT_EXPIRY_INVALID") from exc
    import time
    if expiry <= time.time():
        raise RuntimeError("BRAIN_CONTRACT_EXPIRED")
    dest = pathlib.Path(os.environ.get("BRAIN_WINDOWS_EXECUTION_CONTRACT_FILE",
                                      "/run/brain/windows-execution-contract.json"))
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=dest.name + ".", suffix=".tmp", dir=str(dest.parent))
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(contract, stream, sort_keys=True, separators=(",", ":"))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp_name, dest)
    finally:
        try: os.unlink(tmp_name)
        except FileNotFoundError: pass
    print("BRAIN_CONTRACT_FETCHED=1")
    print("BRAIN_CONTRACT_SOURCE_COMMIT=" + commit)
    print("BRAIN_CONTRACT_ATTEMPT=" + expected["attempt_id"])
    return 0

if __name__ == "__main__":
    try: raise SystemExit(main())
    except RuntimeError as exc:
        print("BRAIN_CONTRACT_FETCH_FAILED=" + str(exc), file=sys.stderr)
        raise SystemExit(2)
