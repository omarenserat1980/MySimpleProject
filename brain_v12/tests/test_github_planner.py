from brain_v12.github_planner import GitHubPlanner

def test_planner_connects_intent_to_tool():
    p=GitHubPlanner().plan("branches")
    assert p.route.domain=="branches"
    assert p.execution.tool=="search_branches"
    assert p.execution.requires_approval is False

def test_planner_blocks_mutating_route_without_approval():
    try:
        GitHubPlanner().plan("workflow_write")
    except PermissionError as e:
        assert str(e)=="GITHUB_APPROVAL_REQUIRED:rerun_workflow_job"
    else:
        raise AssertionError("mutation must be blocked without approval")

def test_describe_does_not_execute_mutation():
    d=GitHubPlanner().describe("code_write")
    assert d["tool"]=="update_file"
    assert d["requires_approval"] is True
    assert d["execution_ready"] is False
