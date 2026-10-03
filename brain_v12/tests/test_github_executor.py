from brain_v12.github_executor import GitHubExecutor

def test_read_tool_plans_without_approval():
    p=GitHubExecutor().plan("fetch_pr")
    assert p.requires_approval is False

def test_mutation_requires_approval():
    try:
        GitHubExecutor().plan("merge_pull_request")
    except PermissionError as e:
        assert str(e)=="GITHUB_APPROVAL_REQUIRED:merge_pull_request"
    else:
        raise AssertionError("mutation must require approval")

def test_unknown_tool_rejected():
    try:
        GitHubExecutor().plan("not_a_real_github_tool")
    except ValueError as e:
        assert str(e)=="UNKNOWN_GITHUB_TOOL:not_a_real_github_tool"
    else:
        raise AssertionError("unknown tool must be rejected")
