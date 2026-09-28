"""Tests for the deterministic repair preflight."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_preflight_script_is_valid(monkeypatch, tmp_path):
    monkeypatch.setenv("FACTORY_ALLOW_LOCAL_FALLBACK", "1")
    report = tmp_path / "preflight.json"
    p = subprocess.run(
        [sys.executable, "-m", "brain_v7.braincore_v2.repair_preflight", "--report", str(report)],
        cwd=ROOT, capture_output=True, text=True, timeout=60,
        env={**os.environ, "FACTORY_ALLOW_LOCAL_FALLBACK": "1"},
    )
    assert p.returncode == 0, p.stdout + p.stderr
    assert report.exists(), p.stdout + p.stderr
    data = json.loads(report.read_text(encoding="utf-8"))
    assert data["status"] == "PREFLIGHT_OK", p.stdout + p.stderr


def test_preflight_report_never_contains_secret_value(monkeypatch, tmp_path):
    monkeypatch.setenv("FACTORY_ALLOW_LOCAL_FALLBACK", "1")
    secret = "super-secret-test-value"
    monkeypatch.setenv("FAL_KEY", secret)
    report = tmp_path / "preflight.json"
    from brain_v7.braincore_v2.repair_preflight import run_preflight
    result = run_preflight(str(report))
    assert result["status"] == "PREFLIGHT_OK"
    assert secret not in report.read_text(encoding="utf-8")
