from brain_v12.github_agent import BrainGitHubAgent

def test_agent_inspect_is_non_mutating():
    a=BrainGitHubAgent({})
    d=a.inspect("pull request")
    assert d["tool"]=="fetch_pr"
    assert d["requires_approval"] is False

def test_agent_executes_read_tool_and_returns_evidence():
    a=BrainGitHubAgent({"fetch_pr": lambda **kw: {"number": 68}})
    out=a.execute("pull request", repo_full_name="omarenserat1980/MySimpleProject", pr_number=68)
    assert out["state"]=="SUCCESS"
    assert out["attempts"]==1
    assert out["evidence"][0]["verification_level"]=="transport"

def test_agent_requires_approval_for_mutation():
    a=BrainGitHubAgent({"merge_pull_request": lambda **kw: {"merged": True}})
    try:
        a.execute("pull request write")
    except PermissionError as e:
        assert str(e)=="GITHUB_APPROVAL_REQUIRED:merge_pull_request"
    else:
        raise AssertionError("mutation bypassed approval")
