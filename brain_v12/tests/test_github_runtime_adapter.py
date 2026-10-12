from brain_v12.github_runtime_adapter import GitHubRuntimeAdapter


class FakeGitHub:
    def configured(self):
        return True


class FakeActionsOperator:
    def __init__(self):
        self.github = FakeGitHub()
        self.calls = []

    def dispatch(self, repo_full_name, workflow_id, **kwargs):
        self.calls.append((repo_full_name, workflow_id, kwargs))
        return {"state": "DISPATCH_ACCEPTED", "workflow": workflow_id}


def test_adapter_blocks_mutation_without_approval():
    a=GitHubRuntimeAdapter({"merge_pull_request": lambda **kw: {"merged": True}})
    try:
        a.call("merge_pull_request")
    except PermissionError as e:
        assert str(e)=="GITHUB_APPROVAL_REQUIRED:merge_pull_request"
    else:
        raise AssertionError("mutation was not blocked")


def test_adapter_dispatches_bound_read_tool():
    a=GitHubRuntimeAdapter({"fetch_pr": lambda **kw: {"number": 68}})
    result=a.call("fetch_pr", repo_full_name="omarenserat1980/MySimpleProject", pr_number=68)
    assert result["number"]==68
    assert a.health()["registered_tools"]==1


def test_adapter_rejects_unbound_registered_tool():
    a=GitHubRuntimeAdapter({})
    try:
        a.call("fetch_pr")
    except RuntimeError as e:
        assert str(e)=="GITHUB_RUNTIME_TOOL_NOT_BOUND:fetch_pr"
    else:
        raise AssertionError("unbound tool was not rejected")


def test_adapter_uses_governed_dispatch_fallback_when_connector_is_missing():
    op = FakeActionsOperator()
    a = GitHubRuntimeAdapter({}, actions_operator=op)
    result = a.call(
        "dispatch_workflow",
        approved=True,
        repo_full_name="omarenserat1980/MySimpleProject",
        workflow_id="brain-ai-core.yml",
        ref="main",
    )
    assert result["state"] == "DISPATCH_ACCEPTED"
    assert op.calls[0][0] == "omarenserat1980/MySimpleProject"
    assert op.calls[0][1] == "brain-ai-core.yml"
    assert a.health()["dispatch_fallback"] == "available"


def test_dispatch_fallback_still_requires_approval():
    a = GitHubRuntimeAdapter({}, actions_operator=FakeActionsOperator())
    try:
        a.call("dispatch_workflow", repo_full_name="owner/repo", workflow_id="workflow.yml")
    except PermissionError as e:
        assert str(e) == "GITHUB_APPROVAL_REQUIRED:dispatch_workflow"
    else:
        raise AssertionError("dispatch bypassed approval")
