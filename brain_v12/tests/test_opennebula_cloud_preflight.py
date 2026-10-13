"""Safety tests for the read-only OpenNebula cloud preflight."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PREFLIGHT = REPO_ROOT / "brain_v12" / "tools" / "opennebula_cloud_preflight.py"

_SPEC = importlib.util.spec_from_file_location("opennebula_cloud_preflight", PREFLIGHT)
assert _SPEC is not None and _SPEC.loader is not None
_PREFLIGHT_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_PREFLIGHT_MODULE)


def test_huda_identity_requires_exact_allowlist_and_machine_id_digest() -> None:
    allowed = _PREFLIGHT_MODULE.huda_host_identity_allowed
    machine_id = "test-machine-id-not-a-real-host-secret"
    digest = hashlib.sha256(machine_id.encode("utf-8")).hexdigest()

    assert allowed("huda-linux-worker-01", machine_id, "huda-linux-worker-01", digest) is True
    assert allowed("huda-linux-worker-01", machine_id, "", digest) is False
    assert allowed("huda-linux-worker-01", "", "huda-linux-worker-01", digest) is False
    assert allowed("huda-linux-worker-01", machine_id, "another-host", digest) is False
    assert allowed("huda-linux-worker-01", machine_id, "huda-linux-worker-01", "bad-digest") is False
    assert allowed("ARKAN", machine_id, "ARKAN", digest) is False
    assert allowed("ark-an-runner", machine_id, "ark-an-runner", digest) is False
    assert allowed("   ", machine_id, "   ", digest) is False


def test_preflight_is_read_only_and_fails_closed_without_identity_allowlist() -> None:
    env = os.environ.copy()
    env.pop("BRAIN_HUDA_ALLOWED_HOSTNAME", None)
    env.pop("BRAIN_HUDA_MACHINE_ID_SHA256", None)
    result = subprocess.run(
        [sys.executable, str(PREFLIGHT)],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )

    assert result.returncode in (0, 2), result.stderr
    payload = json.loads(result.stdout)
    assert payload["mode"] == "read_only"
    assert payload["cloud_name"] == "هدى"
    assert payload["cloud_slug"] == "huda"
    assert payload["provisioned"] is False
    assert payload["vm_created"] is False
    assert payload["status"] == "BLOCKED"
    identity_check = next(item for item in payload["checks"] if item["name"] == "huda_host_identity_verified")
    assert identity_check["ok"] is False
    assert "machine-ID" in identity_check["detail"]
    assert all({"name", "ok", "required", "detail"} <= set(item) for item in payload["checks"])


def test_preflight_redacts_opennebula_endpoint() -> None:
    secret_endpoint = "https://example.invalid/xmlrpc?token=DO_NOT_LEAK_123"
    env = os.environ.copy()
    env["ONE_XMLRPC"] = secret_endpoint
    env.pop("BRAIN_HUDA_ALLOWED_HOSTNAME", None)
    env.pop("BRAIN_HUDA_MACHINE_ID_SHA256", None)
    result = subprocess.run(
        [sys.executable, str(PREFLIGHT)],
        cwd=REPO_ROOT,
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
