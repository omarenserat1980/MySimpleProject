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
        "brain_state": {"value": "RUNNING"},
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
