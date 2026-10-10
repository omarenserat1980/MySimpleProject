#!/usr/bin/env python3
"""Fetch a fresh short-lived attestation from the Brain control plane."""
from __future__ import annotations
import argparse, json, os, tempfile, urllib.error, urllib.request
from pathlib import Path

def post(base: str, path: str, token: str, payload: dict) -> dict:
    request = urllib.request.Request(
        base.rstrip("/") + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-Brain-Executor-Token": token},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("CLOUD_EXECUTOR_REGISTRY_REQUEST_FAILED") from exc
    if not isinstance(result, dict):
        raise RuntimeError("CLOUD_EXECUTOR_REGISTRY_RESPONSE_INVALID")
    return result

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    base = os.environ.get("BRAIN_CLOUD_EXECUTOR_REGISTRY_URL", "").rstrip("/")
    token = os.environ.get("BRAIN_CLOUD_EXECUTOR_TOKEN", "")
    executor_id = os.environ.get("BRAIN_CLOUD_EXECUTOR_ID", "").strip()
    if not base.startswith("https://"):
        raise SystemExit("CLOUD_EXECUTOR_REGISTRY_HTTPS_REQUIRED")
    if not token or not executor_id:
        raise SystemExit("CLOUD_EXECUTOR_REGISTRY_CREDENTIALS_REQUIRED")
    challenge = post(base, "/api/cloud-executor/attestation/challenge", token, {"executor_id": executor_id})
    nonce = challenge.get("nonce", "")
    if challenge.get("executor_id") != executor_id or not isinstance(nonce, str) or len(nonce) < 32:
        raise SystemExit("CLOUD_EXECUTOR_CHALLENGE_RESPONSE_INVALID")
    attestation = post(base, "/api/cloud-executor/attestation/issue", token, {"executor_id": executor_id, "nonce": nonce})
    if attestation.get("executor_id") != executor_id or attestation.get("nonce") != nonce or not attestation.get("signature"):
        raise SystemExit("CLOUD_EXECUTOR_ATTESTATION_RESPONSE_INVALID")
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temp_path = tempfile.mkstemp(prefix=".attestation-", dir=str(destination.parent))
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(attestation, stream, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, destination)
        os.chmod(destination, 0o600)
    finally:
        try:
            os.unlink(temp_path)
        except FileNotFoundError:
            pass
    print("CLOUD_EXECUTOR_ATTESTATION_FETCHED=1")
    print("CLOUD_EXECUTOR_ATTESTATION_PATH=" + str(destination))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
