"""Tests for the deterministic repair preflight."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_preflight_script_is_valid():
    p = subprocess.run(
        [sys.executable, "-m", "brain_v7.braincore_v2.repair_preflight"],
        cwd=ROOT, capture_output=True, text=True, timeout=60,
    )
    data = json.loads(p.stdout)
    assert data["status"] == "PREFLIGHT_OK", p.stdout + p.stderr
