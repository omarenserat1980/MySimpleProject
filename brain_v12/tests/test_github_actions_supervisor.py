from brain_v12.github_actions_supervisor import GitHubActionsSupervisor

def test_cancelled_job_is_auto_rerun():
    d=GitHubActionsSupervisor().decide({"conclusion":"cancelled"})
    assert d.action=="rerun_failed_jobs"
    assert d.automatic is True

def test_real_failure_requires_diagnosis_before_patch():
    d=GitHubActionsSupervisor().decide({
        "conclusion":"failure",
        "steps":[{"name":"tests","conclusion":"failure"}],
    })
    assert d.action=="diagnose_then_patch"
    assert d.automatic is False
