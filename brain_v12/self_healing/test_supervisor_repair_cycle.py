"""Integration tests proving the supervisor can repair a controlled local failure."""

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _command(script: Path) -> str:
    return f"{shlex.quote(sys.executable)} {shlex.quote(str(script))}"


def test_supervisor_repairs_failure_then_verifies_independently(tmp_path):
    marker = tmp_path / "repair-applied.marker"
    target = tmp_path / "target.py"
    repair = tmp_path / "repair.py"
    verify = tmp_path / "verify.py"

    target.write_text(
        "from pathlib import Path\n"
        f"marker = Path({str(marker)!r})\n"
        "if not marker.exists():\n"
        "    print('EXPECTED_PRE_REPAIR_FAILURE')\n"
        "    raise SystemExit(7)\n"
        "print('TARGET_RECOVERED')\n",
        encoding="utf-8",
    )
    repair.write_text(
        "import os\n"
        "from pathlib import Path\n"
        f"Path({str(marker)!r}).write_text('repair applied', encoding='utf-8')\n"
        "assert Path(os.environ['BRAIN_FAILURE_FILE']).exists()\n"
        "print('LOCAL_REPAIR_APPLIED')\n",
        encoding="utf-8",
    )
    verify.write_text(
        "from pathlib import Path\n"
        f"assert Path({str(marker)!r}).exists()\n"
        "print('INDEPENDENT_VERIFY_OK')\n",
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["BRAIN_CHATGPT_REFLECTION"] = "0"
    env.pop("BRAIN_ENABLE_WORKFLOW_ACTIONS", None)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "brain_v12.self_healing.supervisor",
            "--command",
            _command(target),
            "--verify",
            _command(verify),
            "--repair",
            _command(repair),
            "--max-attempts",
            "2",
            "--backoff",
            "0",
            "--max-backoff",
            "0",
            "--timeout",
            "15",
            "--state",
            str(tmp_path / "state"),
        ],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=45,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    history = json.loads(
        (tmp_path / "state" / "self_healing_history.json").read_text(encoding="utf-8")
    )
    assert history["status"] == "VERIFIED_COMPLETED"
    assert len(history["attempts"]) == 2
    first, second = history["attempts"]
    assert first["exit_code"] == 7
    assert first["repair_exit_code"] == 0
    assert "LOCAL_REPAIR_APPLIED" in first["repair_stdout"]
    assert second["exit_code"] == 0
    assert second["verified"] is True
    assert "INDEPENDENT_VERIFY_OK" in second["stdout"]
    assert marker.exists()



def test_supervisor_rejects_repair_when_independent_verifier_fails(tmp_path):
    marker = tmp_path / "repair-applied.marker"
    target = tmp_path / "target.py"
    repair = tmp_path / "repair.py"
    verify = tmp_path / "verify.py"

    target.write_text(
        "from pathlib import Path\\n"
        f"marker = Path({str(marker)!r})\\n"
        "if not marker.exists():\\n"
        "    print('EXPECTED_PRE_REPAIR_FAILURE')\\n"
        "    raise SystemExit(7)\\n"
        "print('TARGET_RECOVERED')\\n",
        encoding="utf-8",
    )
    repair.write_text(
        "import os\\n"
        "from pathlib import Path\\n"
        f"Path({str(marker)!r}).write_text('repair applied', encoding='utf-8')\\n"
        "assert Path(os.environ['BRAIN_FAILURE_FILE']).exists()\\n"
        "print('LOCAL_REPAIR_APPLIED')\\n",
        encoding="utf-8",
    )
    verify.write_text(
        "print('INDEPENDENT_VERIFY_REJECTED')\\n"
        "raise SystemExit(9)\\n",
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["BRAIN_CHATGPT_REFLECTION"] = "0"
    env.pop("BRAIN_ENABLE_WORKFLOW_ACTIONS", None)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "brain_v12.self_healing.supervisor",
            "--command",
            _command(target),
            "--verify",
            _command(verify),
            "--repair",
            _command(repair),
            "--max-attempts",
            "2",
            "--backoff",
            "0",
            "--max-backoff",
            "0",
            "--timeout",
            "15",
            "--state",
            str(tmp_path / "state"),
        ],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=45,
        check=False,
    )

    history = json.loads(
        (tmp_path / "state" / "self_healing_history.json").read_text(encoding="utf-8")
    )
    assert result.returncode != 0
    assert "BRAIN_HEALING_SUCCESS" not in result.stdout
    assert history["status"] == "FAILED_AFTER_REPAIR_ATTEMPTS"
    assert len(history["attempts"]) == 2
    first, second = history["attempts"]
    assert first["exit_code"] == 7
    assert first["repair_exit_code"] == 0
    assert "LOCAL_REPAIR_APPLIED" in first["repair_stdout"]
    assert second["exit_code"] == 9
    assert second["verified"] is False
    assert "INDEPENDENT_VERIFY_REJECTED" in second["stderr"]
    assert marker.exists()
