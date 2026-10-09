import json

from brain_v12.runner_policy_guard import RunnerPolicyGuard


def test_authoritative_workflows_are_brain_runner_only(tmp_path):
    root = tmp_path
    (root / "brain_v12").mkdir()
    (root / ".github" / "workflows").mkdir(parents=True)
    manifest = {
        "policy": "BRAIN_ONLY",
        "external_fallback": False,
        "authoritative_workflows": ["gate.yml"],
    }
    (root / "brain_v12/execution_authority_manifest.json").write_text(json.dumps(manifest))
    (root / ".github/workflows/gate.yml").write_text(
        "runs-on: [self-hosted, brain-runner]\n"
    )
    result = RunnerPolicyGuard(root).validate()
    assert result["healthy"] is True


def test_external_runner_is_blocked(tmp_path):
    root = tmp_path
    (root / "brain_v12").mkdir()
    (root / ".github" / "workflows").mkdir(parents=True)
    manifest = {
        "policy": "BRAIN_ONLY",
        "external_fallback": False,
        "authoritative_workflows": ["gate.yml"],
    }
    (root / "brain_v12/execution_authority_manifest.json").write_text(json.dumps(manifest))
    (root / ".github/workflows/gate.yml").write_text("runs-on: ubuntu-latest\n")
    result = RunnerPolicyGuard(root).validate()
    assert result["healthy"] is False
    assert result["status"] == "BLOCKED"
