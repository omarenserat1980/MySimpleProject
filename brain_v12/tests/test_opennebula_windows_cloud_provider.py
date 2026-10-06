from __future__ import annotations

import json
from pathlib import Path

import pytest

from brain_v12.brain.opennebula_windows_cloud_provider import (
    OpenNebulaWindowsCloudProvider,
)
from brain_v12.brain.windows_cloud_executor import WINDOWS_SERVER_2025


def test_readiness_requires_onevm(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "brain_v12.brain.opennebula_windows_cloud_provider.shutil.which",
        lambda _: None,
    )
    provider = OpenNebulaWindowsCloudProvider()
    result = provider.readiness()
    assert result["ready"] is False
    assert result["reason"] == "OPENNEBULA_ONEVM_NOT_FOUND"


def test_status_maps_running_windows_vm() -> None:
    payload = {
        "VM": {
            "ID": "42",
            "STATE": 3,
            "LCM_STATE": 3,
            "ARCH": "x86_64",
            "TEMPLATE": {
                "BRAIN_OS": WINDOWS_SERVER_2025,
                "BRAIN_REGION": "lab-a",
            },
        }
    }

    def fake_run(cmd, **kwargs):
        assert cmd[1:] == ["show", "42", "--json"]
        return type("R", (), {"stdout": json.dumps(payload)})()

    provider = OpenNebulaWindowsCloudProvider(runner=fake_run)
    vm = provider.status("42")
    assert vm.vm_id == "42"
    assert vm.provider == "opennebula"
    assert vm.region == "lab-a"
    assert vm.state == "RUNNING"
    assert vm.os == WINDOWS_SERVER_2025
    assert vm.architecture == "x86_64"


def test_provision_is_fail_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BRAIN_WINDOWS_CLOUD_ALLOW_APPLY", raising=False)
    provider = OpenNebulaWindowsCloudProvider(
        onevm_bin=str(tmp_path / "onevm"),
        onetemplate_bin=str(tmp_path / "onetemplate"),
    )
    with pytest.raises(RuntimeError, match="EXPLICIT_ENABLEMENT"):
        provider.provision_windows_server_2025()


def test_provision_requires_template_id(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BRAIN_WINDOWS_CLOUD_ALLOW_APPLY", "true")
    monkeypatch.delenv("BRAIN_OPENNEBULA_TEMPLATE_ID", raising=False)
    provider = OpenNebulaWindowsCloudProvider(
        onevm_bin=str(tmp_path / "onevm"),
        onetemplate_bin=str(tmp_path / "onetemplate"),
    )
    with pytest.raises(RuntimeError, match="TEMPLATE_ID_REQUIRED"):
        provider.provision_windows_server_2025()


def test_destroy_is_fail_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BRAIN_WINDOWS_CLOUD_ALLOW_APPLY", raising=False)
    provider = OpenNebulaWindowsCloudProvider(
        onevm_bin=str(tmp_path / "onevm"),
        onetemplate_bin=str(tmp_path / "onetemplate"),
    )
    with pytest.raises(RuntimeError, match="DESTROY_REQUIRES_EXPLICIT_ENABLEMENT"):
        provider.destroy("42")
