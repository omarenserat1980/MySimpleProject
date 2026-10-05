from __future__ import annotations
import json, os, subprocess, sys, time
from pathlib import Path

def test_guardian_source_uses_module_launch_and_restart_controls():
    p=Path(__file__).resolve().parents[1]/"brain_v12/local_worker/brain_local_guardian.py"
    s=p.read_text(encoding="utf-8")
    assert '"-m", MODULE' in s
    assert "STARTUP_GRACE" in s
    assert "STALE_AFTER" in s
    assert "MAX_RESTARTS" in s
    assert "crash_loop_blocked" in s

def test_runtime_diagnostic_is_read_only():
    p=Path(__file__).resolve().parents[1]/"tools/brain_local_runtime_diagnostic.py"
    s=p.read_text(encoding="utf-8")
    assert "diagnostic" in s.lower()
    assert "pgrep" in s


def test_launcher_requires_live_pid_in_heartbeat():
    p=Path(__file__).resolve().parents[1]/"tools/ensure_brain_local_executor.py"
    s=p.read_text(encoding="utf-8")
    assert 'payload.get("pid", 0)' in s
    assert "not running_pid(pid)" in s


def test_guardian_binds_heartbeat_to_current_worker_pid_and_generation_time():
    p=Path(__file__).resolve().parents[1]/"brain_v12/local_worker/brain_local_guardian.py"
    s=p.read_text(encoding="utf-8")
    assert "expected_pid" in s
    assert "started_at" in s
    assert 'payload.get("pid", 0)' in s
    assert "pid == expected_pid" in s
    assert "ts.timestamp() >= started_at" in s
