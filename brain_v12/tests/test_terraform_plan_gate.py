from pathlib import Path

import pytest

from brain_v12.brain.terraform_plan_gate import TerraformPlanGate


def test_requires_init(tmp_path: Path) -> None:
    gate = TerraformPlanGate(tmp_path)
    with pytest.raises(RuntimeError, match="TERRAFORM_INIT_REQUIRED"):
        gate.require_reviewed_plan()


def test_requires_plan(tmp_path: Path) -> None:
    (tmp_path / ".terraform").mkdir()
    gate = TerraformPlanGate(tmp_path)
    with pytest.raises(RuntimeError, match="TERRAFORM_PLAN_REQUIRED"):
        gate.require_reviewed_plan()


def test_accepts_initialized_review_plan(tmp_path: Path) -> None:
    (tmp_path / ".terraform").mkdir()
    (tmp_path / "brain.tfplan").write_bytes(b"opaque-plan")
    gate = TerraformPlanGate(tmp_path)
    assert gate.require_reviewed_plan().name == "brain.tfplan"
