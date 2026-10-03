from brain_v12.github_actions_operator import GitHubActionsOperator, WorkflowEvidence
from brain_v12.github_control_plane import GitHubControlError


class FakeControlPlane:
    def __init__(self):
        self.dispatched = []

    def dispatch_workflow(self, owner, repo, workflow_id, *, ref="main", inputs=None, approved=False):
        if not approved:
            raise GitHubControlError("EXPLICIT_APPROVAL_REQUIRED:actions.write")
        self.dispatched.append((owner, repo, workflow_id, ref, inputs))

    def actions_runs(self, owner, repo, page=1, per_page=50):
        return {"workflow_runs": [{
            "id": 123,
            "name": "Self Healing",
            "path": ".github/workflows/brain-continuous-self-healing.yml",
            "status": "completed",
            "conclusion": "success",
            "created_at": "2999-01-01T00:00:00Z",
        }]}


def test_dispatch_requires_approval():
    op = GitHubActionsOperator(FakeControlPlane())
    try:
        op.dispatch("owner/repo", "workflow.yml")
    except GitHubControlError as exc:
        assert "EXPLICIT_APPROVAL_REQUIRED" in str(exc)
    else:
        raise AssertionError("dispatch bypassed approval")


def test_wait_verifies_completed_success():
    op = GitHubActionsOperator(FakeControlPlane())
    evidence = op.wait_for_run("owner/repo", "workflow.yml", timeout_seconds=1, poll_seconds=1)
    assert isinstance(evidence, WorkflowEvidence)
    assert evidence.verified is True
    assert evidence.run_id == 123


def test_dispatch_and_wait_reports_verified():
    fake = FakeControlPlane()
    result = GitHubActionsOperator(fake).dispatch_and_wait(
        "owner/repo", "workflow.yml", approved=True, timeout_seconds=1, poll_seconds=1
    )
    assert result["verified_completed"] is True
    assert fake.dispatched[0][2] == "workflow.yml"
