"""Allowlisted Brain Fabric job executor.

Security boundary: job payloads cannot supply shell commands or executable
paths. Every executable operation is selected by a fixed internal allowlist.
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path
from typing import Any


ALLOWED_JOB_KINDS = {
    "python_self_test",
    "ffmpeg_probe",
}


def sha256_file(path: str | Path) -> str:
    p = Path(path)
    digest = hashlib.sha256()
    with p.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run(argv: list[str], timeout_seconds: int = 30) -> dict[str, Any]:
    completed = subprocess.run(
        argv,
        capture_output=True,
        text=True,
        timeout=max(1, int(timeout_seconds)),
        check=False,
        shell=False,
    )
    return {
        "argv": argv,
        "returncode": completed.returncode,
        "stdout": completed.stdout[-4000:],
        "stderr": completed.stderr[-4000:],
        "verified": completed.returncode == 0,
    }


def execute_allowlisted(kind: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    if kind not in ALLOWED_JOB_KINDS:
        return {
            "kind": kind,
            "verified": False,
            "status": "REJECTED",
            "reason": "JOB_KIND_NOT_ALLOWLISTED",
        }

    timeout = int(payload.get("timeout_seconds", 30))
    if kind == "python_self_test":
        result = _run(
            [sys.executable, "-c", "import sys; print('BRAIN_PYTHON_SELF_TEST_OK'); sys.exit(0)"],
            timeout,
        )
    else:
        result = _run(["ffmpeg", "-version"], timeout)

    result.update({"kind": kind, "status": "SUCCESS" if result["verified"] else "FAILED"})
    return result
