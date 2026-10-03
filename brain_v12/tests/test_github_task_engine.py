from brain_v12.github_task_engine import GitHubTask, GitHubTaskEngine

def test_task_lifecycle_records_success_evidence():
    e=GitHubTaskEngine()
    t=e.start(GitHubTask("pull request"))
    assert t.state=="RUNNING" and t.attempts==1
    e.record_transport_result(t,"fetch_pr",{"number":68})
    assert t.state=="SUCCESS"
    assert t.evidence[0]["verification_level"]=="transport"

def test_retry_only_failed_tasks():
    e=GitHubTaskEngine()
    t=GitHubTask("actions")
    e.fail(t,"temporary failure")
    assert e.retry(t).state=="RETRYING"

def test_failed_retry_guard():
    e=GitHubTaskEngine()
    t=GitHubTask("actions")
    try:
        e.retry(t)
    except ValueError as exc:
        assert str(exc)=="RETRY_REQUIRES_FAILED:PENDING"
    else:
        raise AssertionError("retry guard failed")
