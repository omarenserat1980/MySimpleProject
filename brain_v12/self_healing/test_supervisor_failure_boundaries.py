"""Failure-boundary tests for the self-healing supervisor.

These tests exercise only temporary local scripts and never modify repository
source files or dispatch remote workflows.
"""

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _command(script: Path) -> str:
    return f"{shlex.quote(sys.executable)} {shlex.quote(str(script))}"


def test_failed_repair_never_claims_success_and_attempts_are_bounded(tmp_path):
    target = tmp_path / "target.py"
    repair = tmp_path / "repair.py"
    verify = tmp_path / "verify.py"
    target.write_text(
        "print('EXPECTED_FAILURE')\nraise SystemExit(7)\n",
        encoding="utf-8",
    )
    repair.write_text(
        "print('REPAIR_FAILED')\nraise SystemExit(9)\n",
        encoding="utf-8",
    )
    verify.write_text(
        "print('VERIFIER_MUST_NOT_CONFIRM')\nraise SystemExit(8)\n",
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["BRAIN_CHATGPT_REFLECTION"] = "0"
    env.pop("BRAIN_ENABLE_WORKFLOW_ACTIONS", None)
    # Keep tests independent of repository/runner-level supervisor defaults.
    env.pop("BRAIN_VERIFY_COMMAND", None)
    env.pop("BRAIN_REPAIR_COMMAND", None)
    state_dir = tmp_path / "state"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "brain_v12.self_healing.supervisor",
            "--command", _command(target),
            "--verify", _command(verify),
            "--repair", _command(repair),
            "--max-attempts", "2",
            "--backoff", "0",
            "--max-backoff", "0",
            "--timeout", "10",
            "--state", str(state_dir),
        ],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=35,
        check=False,
    )

    history_path = state_dir / "self_healing_history.json"
    assert history_path.exists(), result.stdout + result.stderr
    history = json.loads(history_path.read_text(encoding="utf-8"))
    assert result.returncode != 0
    assert history["status"] == "FAILED_AFTER_REPAIR_ATTEMPTS"
    assert 1 <= len(history["attempts"]) <= 2
    assert all(attempt.get("verified") is not True for attempt in history["attempts"])
    assert "BRAIN_HEALING_SUCCESS" not in result.stdout
    assert any(attempt.get("repair_exit_code") == 9 for attempt in history["attempts"])



def test_successful_target_with_failed_independent_verifier_never_claims_success(tmp_path):
    target = tmp_path / "target.py"
    verify = tmp_path / "verify.py"
    target.write_text("print('TARGET_OK')" + chr(10), encoding="utf-8")
    verify.write_text(
        "print('INDEPENDENT_VERIFIER_FAILED')\nraise SystemExit(8)\n",
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["BRAIN_CHATGPT_REFLECTION"] = "0"
    env.pop("BRAIN_ENABLE_WORKFLOW_ACTIONS", None)
    # Keep tests independent of repository/runner-level supervisor defaults.
    env.pop("BRAIN_VERIFY_COMMAND", None)
    env.pop("BRAIN_REPAIR_COMMAND", None)
    state_dir = tmp_path / "state"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "brain_v12.self_healing.supervisor",
            "--command", _command(target),
            "--verify", _command(verify),
            "--max-attempts", "2",
            "--backoff", "0",
            "--max-backoff", "0",
            "--timeout", "10",
            "--state", str(state_dir),
        ],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=35,
        check=False,
    )

    history_path = state_dir / "self_healing_history.json"
    assert history_path.exists(), result.stdout + result.stderr
    history = json.loads(history_path.read_text(encoding="utf-8"))
    assert result.returncode != 0
    assert history["status"] == "FAILED_AFTER_REPAIR_ATTEMPTS"
    assert len(history["attempts"]) == 2
    assert all(attempt.get("verified") is not True for attempt in history["attempts"])
    assert all(attempt.get("exit_code") == 8 for attempt in history["attempts"])
    assert "BRAIN_HEALING_SUCCESS" not in result.stdout
    assert "INDEPENDENT_VERIFIER_FAILED" in result.stdout



def test_successful_target_without_independent_verifier_never_claims_success(tmp_path):
    target = tmp_path / "target.py"
    target.write_text("print('TARGET_OK')" + chr(10), encoding="utf-8")

    env = os.environ.copy()
    env["BRAIN_CHATGPT_REFLECTION"] = "0"
    env.pop("BRAIN_ENABLE_WORKFLOW_ACTIONS", None)
    # Keep tests independent of repository/runner-level supervisor defaults.
    env.pop("BRAIN_VERIFY_COMMAND", None)
    env.pop("BRAIN_REPAIR_COMMAND", None)
    state_dir = tmp_path / "state"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "brain_v12.self_healing.supervisor",
            "--command", _command(target),
            "--max-attempts", "1",
            "--backoff", "0",
            "--max-backoff", "0",
            "--timeout", "10",
            "--state", str(state_dir),
        ],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=35,
        check=False,
    )

    history_path = state_dir / "self_healing_history.json"
    assert history_path.exists(), result.stdout + result.stderr
    history = json.loads(history_path.read_text(encoding="utf-8"))
    assert result.returncode != 0
    assert history["status"] == "FAILED_AFTER_REPAIR_ATTEMPTS"
    assert history["attempts"][0]["verified"] is False
    assert history["attempts"][0]["exit_code"] == 125
    assert "BRAIN_HEALING_SUCCESS" not in result.stdout
