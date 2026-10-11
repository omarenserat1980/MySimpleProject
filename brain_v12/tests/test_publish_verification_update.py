from brain_v12.tools.publish_verification_update import (
    MARKER,
    REQUIRED_WORKFLOWS,
    latest_workflow_states,
    render_comment,
)


def test_missing_runs_fail_closed():
    states = latest_workflow_states([], "abc123")
    body = render_comment(356, "abc123", states)
    assert "BLOCKED / INCOMPLETE" in body
    assert all(states[name] is None for name in REQUIRED_WORKFLOWS)
    assert "MISSING for this exact head" in body


def test_all_required_runs_pass_only_for_exact_head():
    runs = [
        {
            "name": name,
            "head_sha": "abc123",
            "status": "completed",
            "conclusion": "success",
            "id": index + 1,
            "html_url": f"https://github.com/example/run/{index + 1}",
            "created_at": "2026-10-11T10:00:00Z",
        }
        for index, name in enumerate(REQUIRED_WORKFLOWS)
    ]
    runs.append({
        "name": REQUIRED_WORKFLOWS[0],
        "head_sha": "old-sha",
        "status": "completed",
        "conclusion": "success",
        "id": 99,
        "created_at": "2026-10-11T11:00:00Z",
    })
    states = latest_workflow_states(runs, "abc123")
    body = render_comment(356, "abc123", states)
    assert "CI verdict: **PASS**" in body
    assert states[REQUIRED_WORKFLOWS[0]]["id"] == 1
    assert MARKER in body


def test_failed_workflow_blocks_green_verdict():
    runs = [
        {
            "name": name,
            "head_sha": "abc123",
            "status": "completed",
            "conclusion": "success",
            "id": index + 1,
            "created_at": "2026-10-11T10:00:00Z",
        }
        for index, name in enumerate(REQUIRED_WORKFLOWS)
    ]
    runs[2]["conclusion"] = "failure"
    states = latest_workflow_states(runs, "abc123")
    assert "BLOCKED / INCOMPLETE" in render_comment(356, "abc123", states)


def test_in_progress_workflow_blocks_green_verdict():
    runs = [
        {
            "name": name,
            "head_sha": "abc123",
            "status": "completed",
            "conclusion": "success",
            "id": index + 1,
            "created_at": "2026-10-11T10:00:00Z",
        }
        for index, name in enumerate(REQUIRED_WORKFLOWS)
    ]
    runs[0]["status"] = "in_progress"
    runs[0]["conclusion"] = None
    states = latest_workflow_states(runs, "abc123")
    assert "BLOCKED / INCOMPLETE" in render_comment(356, "abc123", states)
