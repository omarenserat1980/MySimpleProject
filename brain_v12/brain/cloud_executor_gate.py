"""Cloud Executor capability gate.

This gate proves only the execution substrate. It does not claim that
Windows Server booted. Production verification requires KVM. An explicit
TCG diagnostic lane may prove that QEMU can start in software emulation, but
it is never reported as a production Cloud Executor verification.
"""
from __future__ import annotations

import json
import os
import platform
import shutil
import socket
import subprocess
import time
from pathlib import Path
from typing import Any


def _run(cmd: list[str], timeout: int = 10) -> tuple[bool, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except Exception as exc:
        return False, f"{type(exc).__name__}:{exc}"
    out = (p.stdout or p.stderr).strip()
    return p.returncode == 0, out


def _probe_accelerator(qemu: str, accelerator: str) -> tuple[bool, str]:
    """Initialize one QEMU accelerator and require it to remain paused."""
    try:
        p = subprocess.Popen(
            [
                qemu,
                "-accel",
                accelerator,
                "-machine",
                "q35",
                "-nodefaults",
                "-display",
                "none",
                "-S",
            ],
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
            return True, f"qemu-initialized-{accelerator}-and-paused"
    except Exception as exc:
        return False, f"{type(exc).__name__}:{exc}"


def check(output: str = "cloud-executor-gate.json") -> dict[str, Any]:
    checks: dict[str, Any] = {}
    mode = os.environ.get("BRAIN_EXECUTOR_ACCELERATOR", "kvm").strip().lower()
    diagnostic_tcg = mode == "tcg-diagnostic"

    cloud_flag = os.environ.get("BRAIN_CLOUD_EXECUTOR", "")
    executor_id = os.environ.get("BRAIN_CLOUD_EXECUTOR_ID", "").strip()
    executor_attestation = os.environ.get("BRAIN_CLOUD_EXECUTOR_ATTESTATION", "").strip()

    if diagnostic_tcg:
        checks["cloud_executor_attestation"] = {
            "ok": True,
            "value": "diagnostic-mode",
        }
        checks["cloud_executor_identity"] = {
            "ok": True,
            "value": "diagnostic-mode",
        }
    else:
        checks["cloud_executor_attestation"] = {
            "ok": bool(executor_attestation),
            "value": "present" if executor_attestation else "missing",
        }
        checks["cloud_executor_identity"] = {
            "ok": cloud_flag == "1" and bool(executor_id),
            "value": executor_id if executor_id else "missing",
        }

    checks["accelerator_mode"] = {
        "ok": mode in {"kvm", "tcg-diagnostic"},
        "value": mode,
    }

    arch = platform.machine().lower()
    checks["x86_64"] = {"ok": arch in {"x86_64", "amd64"}, "value": arch}

    kvm = Path("/dev/kvm")
    if diagnostic_tcg:
        checks["kvm_device"] = {
            "ok": True,
            "value": "not-required-for-tcg-diagnostic",
        }
    else:
        checks["kvm_device"] = {
            "ok": kvm.exists() and os.access(kvm, os.R_OK | os.W_OK),
            "value": str(kvm),
        }

    qemu = shutil.which("qemu-system-x86_64")
    checks["qemu"] = {"ok": bool(qemu), "value": qemu or ""}

    if qemu:
        ok, version = _run([qemu, "--version"])
        checks["qemu_version"] = {
            "ok": ok,
            "value": version.splitlines()[0] if version else "",
        }
        ok, accel = _run([qemu, "-accel", "help"])
        requested_accel = "tcg" if diagnostic_tcg else "kvm"
        checks["qemu_accel"] = {
            "ok": ok and requested_accel in accel.lower(),
            "value": accel[:1000],
        }
        ok, probe = _probe_accelerator(qemu, requested_accel)
        checks["accelerator_runtime"] = {"ok": ok, "value": probe}
    else:
        checks["qemu_version"] = {"ok": False, "value": ""}
        checks["qemu_accel"] = {"ok": False, "value": ""}
        checks["accelerator_runtime"] = {
            "ok": False,
            "value": "qemu-missing",
        }

    checks["python"] = {
        "ok": bool(shutil.which("python") or shutil.which("python3")),
        "value": platform.python_version(),
    }
    checks["hostname"] = {
        "ok": bool(socket.gethostname()),
        "value": socket.gethostname(),
    }
    checks["workdir"] = {
        "ok": os.access(".", os.W_OK),
        "value": str(Path.cwd()),
    }

    substrate_ok = all(v.get("ok") is True for v in checks.values())
    verified = substrate_ok and not diagnostic_tcg
    evidence = {
        "schema": "brain.cloud-executor-gate.v2",
        "verified": verified,
        "diagnostic_verified": substrate_ok if diagnostic_tcg else False,
        "production_capability": "KVM" if not diagnostic_tcg else "TCG-DIAGNOSTIC-ONLY",
        "evidence_ref": f"cloud-executor-gate:{int(time.time())}",
        "executor": "cloud-ephemeral-or-equivalent",
        "executor_id": executor_id,
        "checks": checks,
        "rule": (
            "production: cloud identity + x86_64 + KVM device + QEMU + "
            "actual KVM initialization + writable execution surface; "
            "diagnostic TCG never satisfies production verification"
        ),
    }
    Path(output).write_text(json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8")
    return evidence


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--output", default="cloud-executor-gate.json")
    args = p.parse_args()
    print(json.dumps(check(args.output), indent=2, sort_keys=True))
