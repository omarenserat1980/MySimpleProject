"""Cloud Executor capability gate.

This gate proves only the execution substrate. It does not claim that
Windows Server booted. A Windows capability may proceed only after this
independent substrate gate is VERIFIED.
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
    checks["cloud_executor_identity"] = {
        "ok": cloud_flag == "1",
        "value": "1" if cloud_flag == "1" else "missing",
    }

    arch = platform.machine().lower()
    checks["x86_64"] = {"ok": arch in {"x86_64", "amd64"}, "value": arch}

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
    checks["hostname"] = {"ok": bool(socket.gethostname()), "value": socket.gethostname()}
    checks["workdir"] = {"ok": os.access(".", os.W_OK), "value": str(Path.cwd())}

    verified = all(v.get("ok") is True for v in checks.values())
    evidence = {
        "schema": "brain.cloud-executor-gate.v1",
        "verified": verified,
        "evidence_ref": f"cloud-executor-gate:{int(time.time())}",
        "executor": "cloud-ephemeral-or-equivalent",
        "checks": checks,
        "rule": "cloud identity + x86_64 + KVM device + QEMU + actual KVM initialization + writable execution surface",
    }
    Path(output).write_text(json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8")
    return evidence


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="cloud-executor-gate.json")
    args = p.parse_args()
    print(json.dumps(check(args.output), indent=2, sort_keys=True))
