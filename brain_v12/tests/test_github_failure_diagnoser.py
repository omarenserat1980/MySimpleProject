from brain_v12.github_failure_diagnoser import diagnose

def test_cancelled_run_is_retryable():
    d=diagnose({"conclusion":"cancelled"})
    assert d.category=="cancelled"
    assert d.retryable is True
    assert d.repair=="rerun"

def test_operation_cancelled_is_retryable():
    d=diagnose({"conclusion":"failure"}, "##[error]The operation was canceled.")
    assert d.category=="transient_cancellation"
    assert d.retryable is True

def test_real_step_failure_requires_inspection():
    d=diagnose({"conclusion":"failure","steps":[
        {"name":"tests","conclusion":"failure"}
    ]})
    assert d.category=="step_failure"
    assert d.retryable is False
    assert d.repair=="inspect_and_patch"
