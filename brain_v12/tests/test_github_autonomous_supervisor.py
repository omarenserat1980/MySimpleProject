from brain_v12.github_autonomous_supervisor import GitHubAutonomousSupervisor, SupervisorSession

class DummyAgent: pass

def test_supervisor_requires_ci_and_verification_for_success():
    s=GitHubAutonomousSupervisor(DummyAgent()).start("verify actions")
    s=s.complete(s, ci_passed=True, verification_passed=False)
    assert s.state=="FAILED"

def test_supervisor_accepts_success_only_with_both():
    s=GitHubAutonomousSupervisor(DummyAgent()).start("verify actions")
    s=s.complete(s, ci_passed=True, verification_passed=True)
    assert s.state=="SUCCESS"

def test_supervisor_retry_increments_attempt():
    s=GitHubAutonomousSupervisor(DummyAgent()).start("repair workflow")
    assert s.attempts==1
    s=s.retry(s, "CI failure")
    assert s.state=="RUNNING"
    assert s.attempts==2
    assert s.evidence[-1].stage=="retry"

def test_supervisor_rejects_retry_after_terminal_success():
    s=GitHubAutonomousSupervisor(DummyAgent()).start("done")
    s=s.complete(s, ci_passed=True, verification_passed=True)
    try:
        s=s.retry(s, "unexpected")
    except ValueError as e:
        assert str(e)=="INVALID_RETRY_STATE:SUCCESS"
    else:
        raise AssertionError("terminal task was retried")
