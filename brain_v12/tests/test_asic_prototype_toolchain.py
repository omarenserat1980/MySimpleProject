import subprocess

from brain_v12.asic import toolchain_probe


def test_missing_tools_are_reported_without_installation(monkeypatch):
    monkeypatch.setattr(toolchain_probe.shutil, "which", lambda name: None)
    result = toolchain_probe.probe_toolchain()
    assert result["scope"] == "LOCAL_TOOL_DISCOVERY_ONLY"
    assert result["physical_hardware_access"] is False
    assert set(result["tools"]) == {"iverilog", "verilator", "yosys"}
    assert all(item["status"] == "MISSING" for item in result["tools"].values())


def test_available_tool_records_real_version_command_result(monkeypatch):
    monkeypatch.setattr(toolchain_probe.shutil, "which", lambda name: f"/tools/{name}")

    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(command, 0, stdout="tool version 1.2\n", stderr="")

    monkeypatch.setattr(toolchain_probe.subprocess, "run", fake_run)
    result = toolchain_probe.probe_toolchain()
    assert all(item["status"] == "AVAILABLE" for item in result["tools"].values())
    assert all(item["version"] == "tool version 1.2" for item in result["tools"].values())


def test_failed_version_command_is_not_reported_available(monkeypatch):
    monkeypatch.setattr(toolchain_probe.shutil, "which", lambda name: f"/tools/{name}")

    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(command, 2, stdout="", stderr="bad version command")

    monkeypatch.setattr(toolchain_probe.subprocess, "run", fake_run)
    result = toolchain_probe.probe_toolchain()
    assert all(item["status"] == "VERSION_CHECK_FAILED" for item in result["tools"].values())
