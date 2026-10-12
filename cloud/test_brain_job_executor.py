from pathlib import Path

from cloud.brain_job_executor import execute_allowlisted, sha256_file

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

def test_sha256_artifact_evidence(tmp_path):
    artifact = Path(tmp_path) / "artifact.bin"
    artifact.write_bytes(b"brain-artifact")
    digest = sha256_file(artifact)
    assert len(digest) == 64
    assert digest == "195254b91a5fb3fe0b866e064474fa1de9ae16867de1ccd9071d5a279ebc9918"


def test_invalid_timeout_is_rejected():
    result = execute_allowlisted("python_self_test", {"timeout_seconds": "not-a-number"})
    assert result["verified"] is False
    assert result["reason"] == "INVALID_TIMEOUT"

def test_timeout_is_bounded():
    result = execute_allowlisted("python_self_test", {"timeout_seconds": 999999})
    assert result["verified"] is True
