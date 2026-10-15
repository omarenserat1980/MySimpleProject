"""Regression tests for the self-healing workflow's main-branch write boundary."""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "brain-cloud-mining-control.yml"


def test_cloud_control_validation_workflow_has_read_only_token_permissions():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "permissions:\n  contents: read\n" in workflow
    assert "contents: write" not in workflow


def test_self_healing_validation_does_not_configure_automatic_merge():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    # Validation may run on main and pull requests, but this workflow must
    # remain an observer: no write permission and no merge/push command.
    assert "pull_request:" in workflow
    assert "gh pr merge" not in workflow
    assert "git push" not in workflow
