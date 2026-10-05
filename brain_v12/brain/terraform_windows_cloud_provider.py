from __future__ import annotations

"""Terraform-backed Windows Server 2025 cloud provider.

Provider-specific infrastructure remains in Terraform. Brain consumes only a
small safe output contract and never receives provider secrets.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .terraform_plan_gate import TerraformPlanGate
from .windows_cloud_executor import CloudWindowsVM, WINDOWS_SERVER_2025


class TerraformWindowsCloudProvider:
    name = "terraform"

    def __init__(self, terraform_dir: str | Path | None = None, terraform_bin: str | None = None, *, runner: Any = subprocess.run) -> None:
        self.terraform_dir = Path(terraform_dir or os.environ.get("BRAIN_WINDOWS_TERRAFORM_DIR", ""))
        self.terraform_bin = terraform_bin or os.environ.get("BRAIN_WINDOWS_TERRAFORM_BIN", "terraform")
        self._runner = runner

    def readiness(self) -> dict[str, Any]:
        if not self.terraform_dir.is_dir():
            return {"ready": False, "reason": "TERRAFORM_ROOT_NOT_CONFIGURED"}
        if shutil.which(self.terraform_bin) is None and not Path(self.terraform_bin).is_file():
            return {"ready": False, "reason": "TERRAFORM_BINARY_NOT_FOUND"}
        return {
            "ready": True,
            "provider": self.name,
            "terraform_dir": str(self.terraform_dir),
            "output_contract": [
                "brain_vm_id", "brain_provider", "brain_region",
                "brain_state", "brain_os", "brain_architecture",
            ],
        }

    def provision_windows_server_2025(self, **kwargs: Any) -> CloudWindowsVM:
        self._require_root()
        if os.environ.get("BRAIN_WINDOWS_CLOUD_ALLOW_APPLY", "").lower() != "true":
            raise RuntimeError("WINDOWS_CLOUD_APPLY_REQUIRES_EXPLICIT_ENABLEMENT")
        self._run(["init", "-input=false"])
        plan_path = self.terraform_dir / "brain.tfplan"
        if not plan_path.is_file():
            variables = dict(self._terraform_vars())
            variables.update({k: v for k, v in kwargs.items() if k.startswith("brain_")})
            args = ["plan", "-input=false", "-out=brain.tfplan"]
            for key, value in variables.items():
                args.extend(["-var", f"{key}={value}"])
            self._run(args)
            raise RuntimeError("TERRAFORM_PLAN_CREATED_REVIEW_REQUIRED")
        TerraformPlanGate(self.terraform_dir).require_reviewed_plan()
        self._run(["apply", "-input=false", "brain.tfplan"])
        return self._read_vm()

    def status(self, vm_id: str) -> CloudWindowsVM:
        self._require_root()
        vm = self._read_vm()
        if vm_id and vm.vm_id != vm_id:
            raise RuntimeError("WINDOWS_CLOUD_VM_ID_MISMATCH")
        return vm

    def destroy(self, vm_id: str) -> None:
        self._require_root()
        if os.environ.get("BRAIN_WINDOWS_CLOUD_ALLOW_APPLY", "").lower() != "true":
            raise RuntimeError("WINDOWS_CLOUD_DESTROY_REQUIRES_EXPLICIT_ENABLEMENT")
        vm = self._read_vm()
        if vm_id and vm.vm_id != vm_id:
            raise RuntimeError("WINDOWS_CLOUD_VM_ID_MISMATCH")
        self._run(["destroy", "-auto-approve", "-input=false"])

    def _read_vm(self) -> CloudWindowsVM:
        result = self._run(["output", "-json"])
        raw = json.loads(result.stdout)
        values = {k: v.get("value") if isinstance(v, dict) else v for k, v in raw.items()}
        return CloudWindowsVM(
            vm_id=str(values.get("brain_vm_id", "")),
            provider=str(values.get("brain_provider", "")),
            region=str(values.get("brain_region", "")),
            state=str(values.get("brain_state", "")),
            os=str(values.get("brain_os", WINDOWS_SERVER_2025)),
            architecture=str(values.get("brain_architecture", "x86_64")),
            metadata={"backend": "terraform"},
        )

    def _terraform_vars(self) -> dict[str, Any]:
        try:
            data = json.loads(os.environ.get("BRAIN_WINDOWS_TERRAFORM_VARS_JSON", "{}"))
        except json.JSONDecodeError as exc:
            raise RuntimeError("WINDOWS_CLOUD_TERRAFORM_VARS_INVALID_JSON") from exc
        if not isinstance(data, dict):
            raise RuntimeError("WINDOWS_CLOUD_TERRAFORM_VARS_MUST_BE_OBJECT")
        return data

    def _require_root(self) -> None:
        if not self.terraform_dir.is_dir():
            raise RuntimeError("TERRAFORM_ROOT_NOT_CONFIGURED")

    def _run(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        return self._runner(
            [self.terraform_bin, *args], cwd=self.terraform_dir, check=True,
            capture_output=True, text=True, timeout=1800,
        )
