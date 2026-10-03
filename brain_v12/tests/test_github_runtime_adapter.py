from brain_v12.github_runtime_adapter import GitHubRuntimeAdapter

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
