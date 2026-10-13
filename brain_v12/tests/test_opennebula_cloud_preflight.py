"""Safety tests for the read-only OpenNebula cloud preflight."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PREFLIGHT = REPO_ROOT / "tools" / "opennebula_cloud_preflight.py"


def test_preflight_is_read_only_and_never_claims_provisioning() -> None:
    result = subprocess.run(
        [sys.executable, str(PREFLIGHT)],
        cwd=REPO_ROOT.parent,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )

    assert result.returncode in (0, 2), result.stderr
    payload = json.loads(result.stdout)
    assert payload["mode"] == "read_only"
    assert payload["provisioned"] is False
    assert payload["vm_created"] is False
    assert payload["status"] in {"READY_FOR_REVIEW", "BLOCKED"}
    assert all({"name", "ok", "required", "detail"} <= set(item) for item in payload["checks"])


def test_preflight_redacts_opennebula_endpoint() -> None:
    secret_endpoint = "https://example.invalid/xmlrpc?token=DO_NOT_LEAK_123"
    env = os.environ.copy()
    env["ONE_XMLRPC"] = secret_endpoint
    result = subprocess.run(
        [sys.executable, str(PREFLIGHT)],
        cwd=REPO_ROOT.parent,
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )

    assert result.returncode in (0, 2), result.stderr
    payload = json.loads(result.stdout)
    assert secret_endpoint not in result.stdout
    assert "DO_NOT_LEAK_123" not in result.stdout
    endpoint_check = next(item for item in payload["checks"] if item["name"] == "opennebula_endpoint")
    assert endpoint_check["ok"] is True
    assert endpoint_check["detail"] == "ONE_XMLRPC configured (value redacted)"
