from __future__ import annotations

"""OpenNebula-backed Windows Server 2025 cloud provider.

This adapter intentionally uses the OpenNebula CLI instead of adding a Python
SDK dependency. It is fail-closed: provisioning requires an explicit enable
flag and a pre-created Windows Server 2025 template ID.
"""

import json
import os
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
        target = str(vm_id or "").strip()
        if not target:
            raise RuntimeError("OPENNEBULA_WINDOWS_VM_ID_REQUIRED")
        self._run(self.onevm_bin, ["delete", target])

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
