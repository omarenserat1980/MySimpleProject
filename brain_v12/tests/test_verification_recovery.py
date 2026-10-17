import hashlib

from brain_v12.brain.verification_recovery import (
    VerificationStatus, plan_recovery, verify_file_sha256,
)


def test_file_digest_verifies_matching_artifact(tmp_path):
    artifact = tmp_path / "artifact.bin"
    artifact.write_bytes(b"brain")
    expected = hashlib.sha256(b"brain").hexdigest()
    result = verify_file_sha256(artifact, expected)
    assert result.status == VerificationStatus.VERIFIED
    assert result.actual_sha256 == expected


def test_file_digest_rejects_mismatch_and_missing_file(tmp_path):
    artifact = tmp_path / "artifact.bin"
    artifact.write_bytes(b"changed")
    result = verify_file_sha256(artifact, hashlib.sha256(b"original").hexdigest())
    assert result.status == VerificationStatus.REJECTED
    assert result.reason == "SHA256_MISMATCH"
    missing = verify_file_sha256(tmp_path / "missing.bin", "0" * 64)
    assert missing.reason == "ARTIFACT_UNREADABLE"


def test_recovery_is_bounded_and_only_plans_retry():
    result = plan_recovery(1, 3, retryable=True)
    assert result.retry_allowed is True
    assert result.next_attempt == 2
    assert "NOT_EXECUTED" in result.reason
    assert plan_recovery(3, 3, retryable=True).retry_allowed is False
    assert plan_recovery(1, 3, retryable=False).retry_allowed is False
