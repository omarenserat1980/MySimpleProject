"""Cloud Executor capability gate.

This proves the execution substrate, not Windows boot. Attestation is an
Ed25519-signed, short-lived statement issued by the trusted executor
provisioning service; a non-empty environment string is not sufficient.
"""
from __future__ import annotations

import base64
import json
import os
import platform
import shutil
import socket
import subprocess
import time
from pathlib import Path
from typing import Any

ATTESTATION_SCHEMA = "brain.cloud-executor-attestation.v1"
ATTESTATION_MAX_TTL_SECONDS = 900
ATTESTATION_CLOCK_SKEW_SECONDS = 60
_ATTESTATION_FIELDS = ("schema", "executor_id", "hostname", "architecture", "issued_at", "expires_at")


def _canonical_attestation_payload(attestation: dict[str, Any]) -> bytes:
    payload = {field: attestation.get(field) for field in _ATTESTATION_FIELDS}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _verify_attestation(
    raw: str,
    public_key_b64: str,
    *,
    expected_executor_id: str,
    expected_hostname: str,
    expected_architecture: str,
    now: float | None = None,
) -> tuple[bool, str]:
    """Verify trusted Ed25519 signature, expiry, and exact runner identity binding."""
    if not raw or not public_key_b64:
        return False, "attestation-or-trusted-public-key-missing"
    try:
        attestation = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return False, "attestation-invalid-json"
    if not isinstance(attestation, dict):
        return False, "attestation-not-object"
    if attestation.get("schema") != ATTESTATION_SCHEMA:
        return False, "attestation-schema-invalid"
    for field, expected in (
        ("executor_id", expected_executor_id),
        ("hostname", expected_hostname),
        ("architecture", expected_architecture),
    ):
        if not expected or attestation.get(field) != expected:
            return False, f"attestation-{field}-mismatch"
    issued_at = attestation.get("issued_at")
    expires_at = attestation.get("expires_at")
    if (not isinstance(issued_at, int) or isinstance(issued_at, bool)
            or not isinstance(expires_at, int) or isinstance(expires_at, bool)):
        return False, "attestation-time-invalid"
    current = time.time() if now is None else float(now)
    if issued_at > current + ATTESTATION_CLOCK_SKEW_SECONDS:
        return False, "attestation-issued-in-future"
    if expires_at <= current:
        return False, "attestation-expired"
    if expires_at <= issued_at or expires_at - issued_at > ATTESTATION_MAX_TTL_SECONDS:
        return False, "attestation-lifetime-invalid"
    try:
        public_raw = base64.b64decode(public_key_b64.encode("ascii"), validate=True)
        signature = base64.b64decode(str(attestation.get("signature", "")).encode("ascii"), validate=True)
        if len(public_raw) != 32 or len(signature) != 64:
            return False, "attestation-key-or-signature-length-invalid"
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        Ed25519PublicKey.from_public_bytes(public_raw).verify(signature, _canonical_attestation_payload(attestation))
    except Exception:
        return False, "attestation-signature-invalid"
    return True, "ed25519-signature-valid-and-runner-bound"


def _run(cmd: list[str], timeout: int = 10) -> tuple[bool, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except Exception as exc:
        return False, f"{type(exc).__name__}:{exc}"
    out = (p.stdout or p.stderr).strip()
    return p.returncode == 0, out


def _probe_kvm(qemu: str) -> tuple[bool, str]:
    """Actually initialize KVM in QEMU; timeout means QEMU reached its paused state."""
    try:
        p = subprocess.Popen(
            [qemu, "-accel", "kvm", "-machine", "q35", "-nodefaults", "-display", "none", "-S"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            p.wait(timeout=2)
            err = (p.stderr.read() if p.stderr else "").strip()
            return False, f"qemu-exited:{p.returncode}:{err[:500]}"
        except subprocess.TimeoutExpired:
            p.terminate()
            try:
                p.wait(timeout=2)
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait(timeout=2)
            return True, "qemu-initialized-kvm-and-paused"
    except Exception as exc:
        return False, f"{type(exc).__name__}:{exc}"


def check(output: str = "cloud-executor-gate.json") -> dict[str, Any]:
    checks: dict[str, Any] = {}
    cloud_flag = os.environ.get("BRAIN_CLOUD_EXECUTOR", "")
    executor_id = os.environ.get("BRAIN_CLOUD_EXECUTOR_ID", "").strip()
    raw_attestation = os.environ.get("BRAIN_CLOUD_EXECUTOR_ATTESTATION", "").strip()
    trusted_key = os.environ.get("BRAIN_CLOUD_EXECUTOR_ATTESTATION_PUBLIC_KEY_B64", "").strip()

    arch = platform.machine().lower()
    canonical_arch = "x86_64" if arch in {"x86_64", "amd64"} else arch
    hostname = socket.gethostname()
    attestation_ok, attestation_reason = _verify_attestation(
        raw_attestation,
        trusted_key,
        expected_executor_id=executor_id,
        expected_hostname=hostname,
        expected_architecture=canonical_arch,
    )
    checks["cloud_executor_attestation"] = {"ok": attestation_ok, "value": attestation_reason}
    checks["cloud_executor_identity"] = {
        "ok": cloud_flag == "1" and bool(executor_id),
        "value": executor_id if executor_id else "missing",
    }
    checks["x86_64"] = {"ok": canonical_arch == "x86_64", "value": arch}

    kvm = Path("/dev/kvm")
    checks["kvm_device"] = {"ok": kvm.exists() and os.access(kvm, os.R_OK | os.W_OK), "value": str(kvm)}
    qemu = shutil.which("qemu-system-x86_64")
    checks["qemu"] = {"ok": bool(qemu), "value": qemu or ""}
    if qemu:
        ok, version = _run([qemu, "--version"])
        checks["qemu_version"] = {"ok": ok, "value": version.splitlines()[0] if version else ""}
        ok, accel = _run([qemu, "-accel", "help"])
        checks["qemu_accel"] = {"ok": ok and "kvm" in accel.lower(), "value": accel[:1000]}
        ok, probe = _probe_kvm(qemu)
        checks["kvm_runtime"] = {"ok": ok, "value": probe}
    else:
        checks["qemu_version"] = {"ok": False, "value": ""}
        checks["qemu_accel"] = {"ok": False, "value": ""}
        checks["kvm_runtime"] = {"ok": False, "value": "qemu-missing"}

    checks["python"] = {"ok": bool(shutil.which("python") or shutil.which("python3")), "value": platform.python_version()}
    checks["hostname"] = {"ok": bool(hostname), "value": hostname}
    checks["workdir"] = {"ok": os.access(".", os.W_OK), "value": str(Path.cwd())}
    verified = all(v.get("ok") is True for v in checks.values())
    evidence = {
        "schema": "brain.cloud-executor-gate.v2",
        "verified": verified,
        "evidence_ref": f"cloud-executor-gate:{int(time.time())}",
        "executor": "cloud-ephemeral-or-equivalent",
        "executor_id": executor_id,
        "checks": checks,
        "rule": "trusted Ed25519 runner attestation + exact identity binding + x86_64 + KVM + QEMU + writable execution surface",
    }
    Path(output).write_text(json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8")
    return evidence


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="cloud-executor-gate.json")
    args = p.parse_args()
    print(json.dumps(check(args.output), indent=2, sort_keys=True))
