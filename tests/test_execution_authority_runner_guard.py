import json

from platform_foundation.brain_execution_authority import BrainExecutionAuthority


def test_authority_blocks_when_authoritative_workflow_uses_external_runner(tmp_path):
    root = tmp_path
    (root / "brain_v12").mkdir()
    (root / ".github" / "workflows").mkdir(parents=True)

    manifest = {
        "policy": "BRAIN_ONLY",
        "external_fallback": False,
        "authoritative_workflows": ["gate.yml"],
    }
    (root / "brain_v12/execution_authority_manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    (root / ".github/workflows/gate.yml").write_text(
        "runs-on: ubuntu-latest\n", encoding="utf-8"
    )

    authority = BrainExecutionAuthority(
        executor_id="brain-test",
        heartbeat_path=root / "heartbeat.json",
    )
    authority.heartbeat()

    # Authority uses the repository-root guard by default, so this test
    # verifies the guard contract independently rather than mutating cwd.
    from brain_v12.runner_policy_guard import RunnerPolicyGuard
    guard = RunnerPolicyGuard(root)
    result = guard.validate()

    assert result["healthy"] is False
    assert result["status"] == "BLOCKED"
