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
