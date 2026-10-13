"""Temporary KVM worker provisioner for real Windows boot.

The Brain software node owns the lease lifecycle, but deliberately delegates the
actual host/VM creation to a configured provisioning backend. A backend is only
accepted when it returns a live worker attestation proving Linux x86_64, KVM
read/write, QEMU, and a bounded lease. No simulation is treated as KVM.

Backend contract (stdout JSON):
{
  "worker_id": "brain-kvm-...",
  "endpoint": "...",
  "lease_id": "...",
  "lease_seconds": 900,
  "status": "READY",
  "kvm": {"available": true, "read_write": true},
  "architecture": "x86_64",
  "os": "linux",
  "qemu": true
}

Release backend stdout JSON must contain {"released": true}.
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import time
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class WorkerLease:
    worker_id: str
    endpoint: str
    lease_id: str
    lease_until: float
    status: str = "READY"
    kvm_available: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TemporaryKVMWorkerProvisioner:
    """Fail-closed lease manager for one real-KVM worker."""

    def __init__(self, provision_command: str | None = None,
                 release_command: str | None = None) -> None:
        self.provision_command = provision_command or os.getenv(
            "BRAIN_KVM_WORKER_PROVISION_COMMAND", "").strip()
        self.release_command = release_command or os.getenv(
            "BRAIN_KVM_WORKER_RELEASE_COMMAND", "").strip()
        if not self.provision_command:
            raise RuntimeError("KVM_PROVISION_BACKEND_NOT_CONFIGURED")

    @staticmethod
    def _run(command: str, timeout: int) -> dict[str, Any]:
        proc = subprocess.run(
            shlex.split(command), capture_output=True, text=True,
            timeout=timeout, check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"KVM_BACKEND_FAILED:{proc.returncode}:{proc.stderr[-500:]}"
            )
        try:
            value = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError("KVM_BACKEND_INVALID_JSON") from exc
        if not isinstance(value, dict):
            raise RuntimeError("KVM_BACKEND_OBJECT_REQUIRED")
        return value

    @staticmethod
    def _validate(payload: dict[str, Any]) -> None:
        kvm = payload.get("kvm")
        if payload.get("status") != "READY":
            raise RuntimeError("KVM_WORKER_NOT_READY")
        if payload.get("os") != "linux" or payload.get("architecture") != "x86_64":
            raise RuntimeError("KVM_WORKER_ARCHITECTURE_UNSUPPORTED")
        if payload.get("qemu") is not True:
            raise RuntimeError("QEMU_NOT_ATTESTED")
        if not isinstance(kvm, dict) or kvm.get("available") is not True or kvm.get("read_write") is not True:
            raise RuntimeError("REAL_KVM_NOT_ATTESTED")
        for key in ("worker_id", "endpoint", "lease_id"):
            if not str(payload.get(key, "")).strip():
                raise RuntimeError(f"KVM_WORKER_{key.upper()}_MISSING")
        lease_seconds = int(payload.get("lease_seconds", 0))
        if lease_seconds < 60 or lease_seconds > 3600:
            raise RuntimeError("KVM_WORKER_LEASE_OUT_OF_BOUNDS")

    def provision_once(self, timeout: int = 120) -> WorkerLease:
        payload = self._run(self.provision_command, timeout)
        self._validate(payload)
        return WorkerLease(
            worker_id=str(payload["worker_id"]),
            endpoint=str(payload["endpoint"]),
            lease_id=str(payload["lease_id"]),
            lease_until=time.time() + int(payload["lease_seconds"]),
            kvm_available=True,
        )

    def release(self, lease: WorkerLease, timeout: int = 60) -> dict[str, Any]:
        if not self.release_command:
            raise RuntimeError("KVM_RELEASE_BACKEND_NOT_CONFIGURED")
        command = self.release_command.replace(
            "{lease_id}", shlex.quote(lease.lease_id)
        ).replace("{worker_id}", shlex.quote(lease.worker_id))
        result = self._run(command, timeout)
        if result.get("released") is not True:
            raise RuntimeError("KVM_WORKER_RELEASE_NOT_CONFIRMED")
        return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("provision",))
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args()
    lease = TemporaryKVMWorkerProvisioner().provision_once(args.timeout)
    print(json.dumps(lease.to_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
