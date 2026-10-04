from cloud.brain_job_executor import execute_allowlisted

def test_rejects_arbitrary_job_kind():
    result = execute_allowlisted("run_shell", {"command": "echo unsafe"})
    assert result["verified"] is False
    assert result["reason"] == "JOB_KIND_NOT_ALLOWLISTED"

def test_python_self_test_is_allowlisted():
    result = execute_allowlisted("python_self_test")
    assert result["verified"] is True
    assert result["status"] == "SUCCESS"

def test_ffmpeg_probe_is_allowlisted():
    result = execute_allowlisted("ffmpeg_probe")
    assert result["verified"] is True
    assert result["status"] == "SUCCESS"
