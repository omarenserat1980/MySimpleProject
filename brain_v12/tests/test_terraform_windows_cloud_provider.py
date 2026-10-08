from __future__ import annotations

import json
from pathlib import Path

import pytest

from brain_v12.brain.terraform_windows_cloud_provider import TerraformWindowsCloudProvider


def test_readiness_requires_terraform_root(tmp_path: Path) -> None:
    provider = TerraformWindowsCloudProvider(tmp_path / "missing")
    result = provider.readiness()
    assert result["ready"] is False
    assert result["reason"] == "TERRAFORM_ROOT_NOT_CONFIGURED"


def test_readiness_detects_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "main.tf").write_text("# contract", encoding="utf-8")
    monkeypatch.setattr(
        "brain_v12.brain.terraform_windows_cloud_provider.shutil.which",
        lambda _: "/usr/bin/terraform",
    )
    provider = TerraformWindowsCloudProvider(tmp_path)
    assert provider.readiness()["ready"] is True


def test_status_maps_terraform_outputs(tmp_path: Path) -> None:
    payload = {
        "brain_vm_id": {"value": "vm-123"},
        "brain_provider": {"value": "azure"},
        "brain_region": {"value": "test-region"},
        "brain_state": {"value": "PROVISIONED"},
        "brain_os": {"value": "Windows Server 2025"},
        "brain_architecture": {"value": "x86_64"},
    }

    def fake_run(cmd, **kwargs):
        assert cmd[1:] == ["output", "-json"]
        return type("R", (), {"stdout": json.dumps(payload)})()

    provider = TerraformWindowsCloudProvider(tmp_path, runner=fake_run)
    vm = provider.status("vm-123")
    assert vm.vm_id == "vm-123"
    assert vm.provider == "azure"
    assert vm.state == "RUNNING"
    assert vm.os == "Windows Server 2025"


def test_apply_is_fail_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BRAIN_WINDOWS_CLOUD_ALLOW_APPLY", raising=False)
    provider = TerraformWindowsCloudProvider(tmp_path)
    with pytest.raises(RuntimeError, match="EXPLICIT_ENABLEMENT"):
        provider.provision_windows_server_2025()


def test_apply_creates_plan_then_stops_for_review(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "main.tf").write_text("# contract", encoding="utf-8")
    monkeypatch.setenv("BRAIN_WINDOWS_CLOUD_ALLOW_APPLY", "true")
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd[1:])
        return type("R", (), {"stdout": ""})()

    provider = TerraformWindowsCloudProvider(tmp_path, runner=fake_run)
    with pytest.raises(RuntimeError, match="PLAN_CREATED_REVIEW_REQUIRED"):
        provider.provision_windows_server_2025()
    assert calls[0] == ["init", "-input=false"]
    assert calls[1][:3] == ["plan", "-input=false", "-out=brain.tfplan"]
    assert not any(cmd[0] == "apply" for cmd in calls)


def test_apply_uses_existing_plan_only_after_explicit_approval(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "main.tf").write_text("# contract", encoding="utf-8")
    (tmp_path / ".terraform").mkdir()
    (tmp_path / "brain.tfplan").write_bytes(b"opaque")
    monkeypatch.setenv("BRAIN_WINDOWS_CLOUD_ALLOW_APPLY", "true")
    monkeypatch.delenv("BRAIN_WINDOWS_CLOUD_PLAN_APPROVED", raising=False)

    def fake_run(cmd, **kwargs):
        return type("R", (), {"stdout": ""})()

    provider = TerraformWindowsCloudProvider(tmp_path, runner=fake_run)
    with pytest.raises(RuntimeError, match="PLAN_EXPLICIT_APPROVAL_REQUIRED"):
        provider.provision_windows_server_2025()


def test_approved_apply_uses_plan_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "main.tf").write_text("# contract", encoding="utf-8")
    (tmp_path / ".terraform").mkdir()
    (tmp_path / "brain.tfplan").write_bytes(b"opaque")
    monkeypatch.setenv("BRAIN_WINDOWS_CLOUD_ALLOW_APPLY", "true")
    monkeypatch.setenv("BRAIN_WINDOWS_CLOUD_PLAN_APPROVED", "true")
    payload = {
        "brain_vm_id": {"value": "vm-123"},
        "brain_provider": {"value": "azure"},
        "brain_region": {"value": "test-region"},
        "brain_state": {"value": "RUNNING"},
        "brain_os": {"value": "Windows Server 2025"},
        "brain_architecture": {"value": "x86_64"},
    }
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd[1:])
        if cmd[1:] == ["output", "-json"]:
            return type("R", (), {"stdout": json.dumps(payload)})()
        return type("R", (), {"stdout": ""})()

    provider = TerraformWindowsCloudProvider(tmp_path, runner=fake_run)
    vm = provider.provision_windows_server_2025()
    assert vm.vm_id == "vm-123"
    assert ["apply", "-input=false", "brain.tfplan"] in calls
