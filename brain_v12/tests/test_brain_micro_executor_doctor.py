"""Tests for the read-only Brain Micro-Executor doctor."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "brain_micro_executor_doctor.py"


def make_repo(root: Path, *, optional: bool = False) -> None:
    (root / ".git").mkdir()
    (root / "brain_v12" / "tools").mkdir(parents=True)
    (root / "brain_v12" / "app.py").write_text("# app\n", encoding="utf-8")
    (root / "brain_v12" / "tools" / "brain_runtime_launcher.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    if optional:
        (root / "brain_v12" / "tools" / "brain_device_bridge_doctor.py").write_text("# optional\n", encoding="utf-8")


def run_doctor(root: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PREFIX"] = "/data/data/com.termux/files/usr"
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), "--json"],
        check=False, capture_output=True, text=True, env=env, timeout=10,
    )


def test_doctor_passes_with_required_files_and_optional_files_absent(tmp_path: Path) -> None:
    make_repo(tmp_path)
    result = run_doctor(tmp_path)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["mode"] == "READ_ONLY"
    assert payload["task_polling"] is False
    assert payload["worker_registration"] is False
    assert payload["remote_requests"] is False
    assert payload["configuration_changes"] is False
    assert payload["checks_passed"] == payload["checks_total"]
    optional = [item for item in payload["checks"] if item["name"].startswith("optional_file:")]
    assert optional and all(item["ok"] for item in optional)


def test_doctor_fails_when_required_file_is_missing(tmp_path: Path) -> None:
    make_repo(tmp_path)
    (tmp_path / "brain_v12" / "app.py").unlink()
    result = run_doctor(tmp_path)
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    required = [item for item in payload["checks"] if item["name"].startswith("required_file:")]
    assert any(not item["ok"] for item in required)
