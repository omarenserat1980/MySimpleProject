from __future__ import annotations

"""OpenNebula-backed Windows Server 2025 cloud provider.

This adapter intentionally uses the OpenNebula CLI instead of adding a Python
SDK dependency. It is fail-closed: provisioning requires an explicit enable
flag and a pre-created Windows Server 2025 template ID.
"""

import hashlib
import json
import os
import platform
from pathlib import Path
import shutil
import subprocess
from typing import Any

from .windows_cloud_executor import CloudWindowsVM, WINDOWS_SERVER_2025


class OpenNebulaWindowsCloudProvider:
    name = "opennebula"

    def __init__(
        self,
        onevm_bin: str | None = None,
        onetemplate_bin: str | None = None,
        *,
        runner: Any = subprocess.run,
    ) -> None:
        self.onevm_bin = onevm_bin or os.environ.get("BRAIN_OPENNEBULA_ONEVM_BIN", "onevm")
        self.onetemplate_bin = onetemplate_bin or os.environ.get(
            "BRAIN_OPENNEBULA_ONETEMPLATE_BIN", "onetemplate"
        )
        self._runner = runner

    def readiness(self) -> dict[str, Any]:
        if shutil.which(self.onevm_bin) is None and not os.path.isfile(self.onevm_bin):
            return {"ready": False, "provider": self.name, "reason": "OPENNEBULA_ONEVM_NOT_FOUND"}
        if shutil.which(self.onetemplate_bin) is None and not os.path.isfile(self.onetemplate_bin):
            return {
                "ready": False,
                "provider": self.name,
                "reason": "OPENNEBULA_ONETEMPLATE_NOT_FOUND",
            }
        template_id = os.environ.get("BRAIN_OPENNEBULA_TEMPLATE_ID", "").strip()
        vm_id = os.environ.get("BRAIN_OPENNEBULA_VM_ID", "").strip()
        return {
            "ready": True,
            "provider": self.name,
            "template_id_configured": bool(template_id),
            "vm_id_configured": bool(vm_id),
            "output_contract": [
                "vm_id",
                "provider",
                "region",
                "state",
                "os",
                "architecture",
            ],
        }

    def provision_windows_server_2025(self, **kwargs: Any) -> CloudWindowsVM:
        if os.environ.get("BRAIN_WINDOWS_CLOUD_ALLOW_APPLY", "").lower() != "true":
            raise RuntimeError("WINDOWS_CLOUD_APPLY_REQUIRES_EXPLICIT_ENABLEMENT")
        self._assert_huda_host_identity()

        template_id = str(
            kwargs.get("opennebula_template_id")
            or os.environ.get("BRAIN_OPENNEBULA_TEMPLATE_ID", "")
        ).strip()
        if not template_id:
            raise RuntimeError("OPENNEBULA_WINDOWS_TEMPLATE_ID_REQUIRED")

        name = str(kwargs.get("name") or os.environ.get("BRAIN_OPENNEBULA_VM_NAME", "")).strip()
        args = ["instantiate", template_id]
        if name:
            args.extend(["--name", name])
        result = self._run(self.onetemplate_bin, args)
        vm_id = self._parse_vm_id(result.stdout)
        return self.status(vm_id)

    def status(self, vm_id: str) -> CloudWindowsVM:
        target = str(vm_id or os.environ.get("BRAIN_OPENNEBULA_VM_ID", "")).strip()
        if not target:
            raise RuntimeError("OPENNEBULA_WINDOWS_VM_ID_REQUIRED")
        result = self._run(self.onevm_bin, ["show", target, "--json"])
        raw = json.loads(result.stdout)
        vm = raw.get("VM", raw)
        return self._to_cloud_vm(vm)

    def destroy(self, vm_id: str) -> None:
        if os.environ.get("BRAIN_WINDOWS_CLOUD_ALLOW_APPLY", "").lower() != "true":
            raise RuntimeError("WINDOWS_CLOUD_DESTROY_REQUIRES_EXPLICIT_ENABLEMENT")
        self._assert_huda_host_identity()
        target = str(vm_id or "").strip()
        if not target:
            raise RuntimeError("OPENNEBULA_WINDOWS_VM_ID_REQUIRED")
        self._run(self.onevm_bin, ["delete", target])

    @staticmethod
    def _read_machine_id() -> str:
        for candidate in (Path("/etc/machine-id"), Path("/var/lib/dbus/machine-id")):
            try:
                value = candidate.read_text(encoding="utf-8").strip()
            except OSError:
                continue
            if value:
                return value
        return ""

    @classmethod
    def _assert_huda_host_identity(cls) -> None:
        """Require the provisioner to run on an explicitly allowlisted Huda host."""
        hostname = platform.node().strip().lower()
        allowed_hostname = os.environ.get("BRAIN_HUDA_ALLOWED_HOSTNAME", "").strip().lower()
        machine_id = cls._read_machine_id()
        expected_digest = os.environ.get("BRAIN_HUDA_MACHINE_ID_SHA256", "").strip().lower()
        if "arkan" in hostname or "ark-an" in hostname:
            raise RuntimeError("ARKAN_FORBIDDEN")
        if not hostname or not allowed_hostname or hostname != allowed_hostname:
            raise RuntimeError("HUDA_HOST_IDENTITY_NOT_ALLOWLISTED")
        if not machine_id or len(expected_digest) != 64 or any(c not in "0123456789abcdef" for c in expected_digest):
            raise RuntimeError("HUDA_HOST_IDENTITY_EVIDENCE_MISSING")
        actual_digest = hashlib.sha256(machine_id.encode("utf-8")).hexdigest()
        if actual_digest != expected_digest:
            raise RuntimeError("HUDA_HOST_IDENTITY_MISMATCH")

    @staticmethod
    def _parse_vm_id(stdout: str) -> str:
        for token in stdout.replace("\n", " ").split():
            if token.isdigit():
                return token
        raise RuntimeError("OPENNEBULA_VM_ID_NOT_RETURNED")

    @staticmethod
    def _to_cloud_vm(vm: dict[str, Any]) -> CloudWindowsVM:
        vm_id = str(vm.get("ID", "")).strip()
        template = vm.get("TEMPLATE") or {}
        state = OpenNebulaWindowsCloudProvider._state(vm)
        os_name = str(
            template.get("BRAIN_OS")
            or template.get("OS")
            or os.environ.get("BRAIN_OPENNEBULA_WINDOWS_OS", WINDOWS_SERVER_2025)
        ).strip()
        architecture = str(
            vm.get("ARCH")
            or template.get("ARCH")
            or "x86_64"
        ).strip()
        region = str(
            template.get("BRAIN_REGION")
            or os.environ.get("BRAIN_OPENNEBULA_REGION", "opennebula")
        ).strip()
        if not vm_id:
            raise RuntimeError("OPENNEBULA_VM_ID_MISSING")
        return CloudWindowsVM(
            vm_id=vm_id,
            provider="opennebula",
            region=region,
            state=state,
            os=os_name,
            architecture=architecture,
            metadata={"backend": "opennebula"},
        )

    @staticmethod
    def _state(vm: dict[str, Any]) -> str:
        state = str(vm.get("STATE", "")).upper()
        lcm_state = str(vm.get("LCM_STATE", "")).upper()
        if state in {"3", "ACTIVE"} and lcm_state in {"3", "RUNNING"}:
            return "RUNNING"
        if state in {"8", "POWEROFF"}:
            return "STOPPED"
        if state in {"4", "STOPPED"}:
            return "STOPPED"
        if state in {"7", "FAILED"}:
            return "FAILED"
        return state or lcm_state or "UNKNOWN"

    def _run(self, binary: str, args: list[str]) -> subprocess.CompletedProcess[str]:
        return self._runner(
            [binary, *args],
            check=True,
            capture_output=True,
            text=True,
            timeout=1800,
        )
