from brain_v12.tools.publish_verification_update import (
    MARKER, REQUIRED_WORKFLOWS, latest_workflow_states, render_comment,
)

def make_runs(head="abc123"):
    return [{
        "name": name, "head_sha": head, "status": "completed", "conclusion": "success",
        "id": i + 1, "html_url": f"https://github.com/example/runs/{i + 1}",
        "created_at": "2026-10-11T10:00:00Z",
    } for i, name in enumerate(REQUIRED_WORKFLOWS)]

def test_missing_evidence_fails_closed():
    states = latest_workflow_states([], "abc123")
    body = render_comment(356, "abc123", states)
    assert "BLOCKED / INCOMPLETE" in body
    assert "MISSING for this exact head" in body

def test_success_requires_all_five_workflows_for_exact_head():
    runs = make_runs()
    runs.append({**make_runs("old-sha")[0], "id": 99, "created_at": "2026-10-11T11:00:00Z"})
    states = latest_workflow_states(runs, "abc123")
    body = render_comment(356, "abc123", states)
    assert "CI verdict: **PASS**" in body
    assert states[REQUIRED_WORKFLOWS[0]]["id"] == 1
    assert MARKER in body

def test_failure_blocks_green_verdict():
    runs = make_runs()
    runs[2]["conclusion"] = "failure"
    assert "BLOCKED / INCOMPLETE" in render_comment(356, "abc123", latest_workflow_states(runs, "abc123"))

def test_in_progress_blocks_green_verdict():
    runs = make_runs()
    runs[0]["status"] = "in_progress"
    runs[0]["conclusion"] = None
    assert "BLOCKED / INCOMPLETE" in render_comment(356, "abc123", latest_workflow_states(runs, "abc123"))
