from brain_v12.github_capability_registry import GITHUB_TOOL_COUNT, GITHUB_TOOLS, WRITE_OR_MUTATING_TOOLS, capability_catalog, has_tool

def test_github_tool_surface_is_complete():
    assert GITHUB_TOOL_COUNT == 90
    assert len(GITHUB_TOOLS) == 90
    assert has_tool("fetch_pr")
    assert has_tool("merge_pull_request")
    assert has_tool("fetch_workflow_job_logs")
    assert has_tool("dispatch_workflow")
    assert has_tool("update_file")

def test_mutations_are_gated():
    assert "merge_pull_request" in WRITE_OR_MUTATING_TOOLS
    assert "update_file" in WRITE_OR_MUTATING_TOOLS
    assert "dispatch_workflow" in WRITE_OR_MUTATING_TOOLS
    assert "fetch_pr" not in WRITE_OR_MUTATING_TOOLS
    assert capability_catalog()["tool_count"] == 90
