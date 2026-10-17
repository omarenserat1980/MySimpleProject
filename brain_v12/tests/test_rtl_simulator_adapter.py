from types import SimpleNamespace

import pytest

from brain_v12.brain import rtl_simulator_adapter as rtl


def test_missing_rtl_toolchain_fails_closed(monkeypatch):
    monkeypatch.setattr(rtl.shutil, "which", lambda name: None)
    result = rtl.run_sha256d_rtl_self_test()
    assert result["status"] == "BLOCKED_TOOLCHAIN_UNAVAILABLE"
    assert result["rtl_executed"] is False
    assert result["evidence_status"] == "BLOCKED"
    assert result["software_hashing_substituted"] is False


def test_invalid_timeout_fails_before_running_tools(monkeypatch):
    monkeypatch.setattr(rtl.shutil, "which", lambda name: "/usr/bin/" + name)
    result = rtl.run_sha256d_rtl_self_test(timeout_seconds=0)
    assert result["status"] == "INVALID_TIMEOUT"
    assert result["rtl_executed"] is False


def test_expected_rtl_marker_and_genesis_nonce_are_required(monkeypatch):
    monkeypatch.setattr(rtl.shutil, "which", lambda name: "/usr/bin/" + name)
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        if command[0].endswith("iverilog"):
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        return SimpleNamespace(
            returncode=0,
            stdout=(
                "PASS BITCOIN_GENESIS_NONCE_FOUND nonce=7c2bac1d attempts=2\n"
                "ALL_GENESIS_NONCE_SEARCH_TESTS_PASSED\n"
            ),
            stderr="",
        )

    monkeypatch.setattr(rtl.subprocess, "run", fake_run)
    result = rtl.run_sha256d_rtl_self_test()
    assert result["status"] == "VERIFIED"
    assert result["rtl_executed"] is True
    assert result["evidence_status"] == "RTL_SIMULATION_VERIFIED"
    assert len(calls) == 2
    assert calls[0][0].endswith("iverilog")
    assert calls[1][0].endswith("vvp")
    assert result["physical_asic_executed"] is False
    assert result["pool_acceptance_verified"] is False
    assert result["revenue_verified"] is False


def test_missing_expected_marker_never_becomes_verified(monkeypatch):
    monkeypatch.setattr(rtl.shutil, "which", lambda name: "/usr/bin/" + name)

    def fake_run(command, **kwargs):
        if command[0].endswith("iverilog"):
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        return SimpleNamespace(returncode=0, stdout="simulation finished\n", stderr="")

    monkeypatch.setattr(rtl.subprocess, "run", fake_run)
    result = rtl.run_sha256d_rtl_self_test()
    assert result["status"] == "RTL_RESULT_UNVERIFIED"
    assert result["rtl_executed"] is False
    assert result["evidence_status"] == "BLOCKED"


def test_nonzero_compile_is_not_rtl_success(monkeypatch):
    monkeypatch.setattr(rtl.shutil, "which", lambda name: "/usr/bin/" + name)
    monkeypatch.setattr(
        rtl.subprocess, "run",
        lambda command, **kwargs: SimpleNamespace(returncode=1, stdout="", stderr="syntax error"),
    )
    result = rtl.run_sha256d_rtl_self_test()
    assert result["status"] == "RTL_COMPILE_FAILED"
    assert result["rtl_executed"] is False


def test_simulation_timeout_fails_closed(monkeypatch):
    monkeypatch.setattr(rtl.shutil, "which", lambda name: "/usr/bin/" + name)

    def fake_run(command, **kwargs):
        if command[0].endswith("iverilog"):
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        raise rtl.subprocess.TimeoutExpired(command, kwargs.get("timeout"))

    monkeypatch.setattr(rtl.subprocess, "run", fake_run)
    result = rtl.run_sha256d_rtl_self_test()
    assert result["status"] == "RTL_SIMULATION_TIMEOUT"
    assert result["rtl_executed"] is False
