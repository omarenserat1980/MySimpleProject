from types import SimpleNamespace

import pytest

from brain_v12.brain import rtl_simulator_adapter as rtl


class FakeProcess:
    def __init__(self, command, *, returncode=0, stdout="", stderr="", never_finishes=False):
        self.command = command
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.never_finishes = never_finishes
        self.terminated = False
        self.killed = False

    def poll(self):
        return None if self.never_finishes and not self.terminated and not self.killed else self.returncode

    def communicate(self, timeout=None):
        return self.stdout, self.stderr

    def terminate(self):
        self.terminated = True
        self.returncode = -15

    def kill(self):
        self.killed = True
        self.returncode = -9


def setup_tools(monkeypatch, *, simulation_stdout="", compile_returncode=0, simulation_returncode=0, never_finishes=False):
    monkeypatch.setattr(rtl.shutil, "which", lambda name: "/usr/bin/" + name)

    def fake_popen(command, **kwargs):
        if command[0].endswith("iverilog"):
            return FakeProcess(command, returncode=compile_returncode, stderr="compile error" if compile_returncode else "")
        return FakeProcess(
            command, returncode=simulation_returncode, stdout=simulation_stdout,
            never_finishes=never_finishes,
        )

    monkeypatch.setattr(rtl.subprocess, "Popen", fake_popen)


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
    setup_tools(
        monkeypatch,
        simulation_stdout=(
            "PASS BITCOIN_GENESIS_NONCE_FOUND nonce=7c2bac1d attempts=2\n"
            "ALL_GENESIS_NONCE_SEARCH_TESTS_PASSED\n"
        ),
    )
    calls = []
    original = rtl.subprocess.Popen

    def tracking_popen(command, **kwargs):
        calls.append(command)
        return original(command, **kwargs)

    monkeypatch.setattr(rtl.subprocess, "Popen", tracking_popen)
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
    setup_tools(monkeypatch, simulation_stdout="simulation finished\n")
    result = rtl.run_sha256d_rtl_self_test()
    assert result["status"] == "RTL_RESULT_UNVERIFIED"
    assert result["rtl_executed"] is False
    assert result["evidence_status"] == "BLOCKED"


def test_nonzero_compile_is_not_rtl_success(monkeypatch):
    setup_tools(monkeypatch, compile_returncode=1)
    result = rtl.run_sha256d_rtl_self_test()
    assert result["status"] == "RTL_COMPILE_FAILED"
    assert result["rtl_executed"] is False


def test_simulation_timeout_fails_closed(monkeypatch):
    setup_tools(monkeypatch, never_finishes=True)
    # Deadline, compile budget, compile start, simulation budget, simulation start, then timeout.
    times = iter([0.0, 0.0, 0.0, 0.0, 0.0, 0.2])
    monkeypatch.setattr(rtl.time, "monotonic", lambda: next(times))
    monkeypatch.setattr(rtl.time, "sleep", lambda _: None)
    result = rtl.run_sha256d_rtl_self_test(timeout_seconds=0.1)
    assert result["status"] == "RTL_SIMULATION_TIMEOUT"
    assert result["rtl_executed"] is False


def test_simulation_cancellation_terminates_process_and_never_succeeds(monkeypatch):
    setup_tools(monkeypatch, never_finishes=True)
    calls = iter([False, True])
    result = rtl.run_sha256d_rtl_self_test(cancel_check=lambda: next(calls))
    assert result["status"] == "RTL_CANCELLED"
    assert result["error_code"] == "CANCELLED_DURING_SIMULATION"
    assert result["rtl_executed"] is False
    assert result["evidence_status"] == "BLOCKED"
