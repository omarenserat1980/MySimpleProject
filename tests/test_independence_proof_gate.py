import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_independence_proof_gate_runs_without_github_credentials(tmp_path):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    for key in ("GITHUB_TOKEN", "GH_TOKEN", "GIT_ASKPASS"):
        env.pop(key, None)

    result = subprocess.run(
        [sys.executable, "tools/brain_independence_proof_gate.py"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    report = json.loads(
        (ROOT / "brain6_artifacts" / "independence_gate" / "independence_proof.json")
        .read_text(encoding="utf-8")
    )
    assert report["status"] == "PROVEN_WITHIN_TEST_SCOPE"
    assert report["independence_claim_allowed"] is True
    assert report["checks"]["base_expansion_integrity"] is True
    assert report["checks"]["real_worker_execution"] is True
    assert report["checks"]["authority_boundary_negative_tests"] is True
    assert report["checks"]["github_credentials_removed"] is True
    assert report["checks"]["network_dependency_for_gate"] is False
    assert report["scope"]["authority_boundary"] is True
