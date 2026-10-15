"""End-to-end tests for the self-healing supervisor's evidence contract."""

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _python_command(source: str) -> str:
    return f"{shlex.quote(sys.executable)} -c {shlex.quote(source)}"


def _run_supervisor(state_dir: Path, verify_source: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["BRAIN_CHATGPT_REFLECTION"] = "0"
    env.pop("BRAIN_ENABLE_WORKFLOW_ACTIONS", None)
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "brain_v12.self_healing.supervisor",
            "--command",
            _python_command("print('TARGET_OK')"),
            "--verify",
            _python_command(verify_source),
            "--max-attempts",
            "1",
            "--backoff",
            "0",
            "--max-backoff",
            "0",
            "--timeout",
            "15",
            "--state",
            str(state_dir),
        ],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )


def test_supervisor_persists_verified_completion_evidence(tmp_path):
    result = _run_supervisor(tmp_path / "state", "print('VERIFY_OK')")

    assert result.returncode == 0, result.stdout + result.stderr
    history = json.loads((tmp_path / "state" / "self_healing_history.json").read_text())
    assert history["schema"] == "brain-self-healing/v1"
    assert history["status"] == "VERIFIED_COMPLETED"
    assert len(history["attempts"]) == 1
    assert history["attempts"][0]["verified"] is True
    assert "VERIFY_OK" in history["attempts"][0]["stdout"]


def test_supervisor_rejects_success_when_verification_fails(tmp_path):
    result = _run_supervisor(tmp_path / "state", "raise SystemExit(7)")

    assert result.returncode != 0
    history = json.loads((tmp_path / "state" / "self_healing_history.json").read_text())
    assert history["status"] == "FAILED_AFTER_REPAIR_ATTEMPTS"
    assert history["attempts"][0]["verified"] is False
    assert history["attempts"][0]["exit_code"] == 7
    assert "BRAIN_HEALING_SUCCESS" not in result.stdout
