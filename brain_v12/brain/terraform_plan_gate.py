from __future__ import annotations

"""Fail-closed Terraform plan gate for Brain Windows Cloud."""

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class TerraformPlanGate:
    root: Path

    def inspect(self) -> dict[str, object]:
        plan = self.root / "brain.tfplan"
        lock = self.root / ".terraform.lock.hcl"
        initialized = (self.root / ".terraform").is_dir()

        return {
            "ready": initialized and plan.is_file(),
            "initialized": initialized,
            "plan_present": plan.is_file(),
            "lockfile_present": lock.is_file(),
            "reason": (
                "TERRAFORM_PLAN_READY"
                if initialized and plan.is_file()
                else "TERRAFORM_PLAN_REQUIRED"
            ),
        }

    def require_reviewed_plan(self) -> Path:
        state = self.inspect()
        if not state["initialized"]:
            raise RuntimeError("TERRAFORM_INIT_REQUIRED")
        if not state["plan_present"]:
            raise RuntimeError("TERRAFORM_PLAN_REQUIRED")
        if os.environ.get("BRAIN_WINDOWS_CLOUD_PLAN_APPROVED", "").lower() != "true":
            raise RuntimeError("TERRAFORM_PLAN_EXPLICIT_APPROVAL_REQUIRED")
        return self.root / "brain.tfplan"
