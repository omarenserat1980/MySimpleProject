import json

from brain_v12.brain.cloud_executor_attestation_api import attestation_status


def test_status_reports_configured_but_never_claims_live_identity(monkeypatch, tmp_path):
    registry = tmp_path / "registry.sqlite3"
    monkeypatch.setenv("BRAIN_CLOUD_EXECUTOR_REGISTRY_DB", str(registry))
    monkeypatch.setenv("BRAIN_EXECUTOR_ATTESTATION_SIGNING_KEY_B64", "test-key-present")
    monkeypatch.setenv(
        "BRAIN_CLOUD_EXECUTOR_ENROLLMENTS_SHA256_JSON",
        json.dumps({"test-executor": "a" * 64}),
    )
    monkeypatch.setenv(
        "BRAIN_CLOUD_EXECUTOR_HOST_BINDINGS_JSON",
        json.dumps({"test-executor": {"hostname": "worker-test", "architecture": "x86_64"}}),
    )

    result = attestation_status()

    assert result["status"] == "CONFIGURED_UNVERIFIED"
    assert result["control_plane_configured"] is True
    assert result["live_attestation_verified"] is False
    assert result["physical_hardware_verified"] is False
    assert "test-key-present" not in str(result)
    assert "worker-test" not in str(result)


def test_status_fails_closed_when_required_configuration_is_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAIN_CLOUD_EXECUTOR_REGISTRY_DB", str(tmp_path / "registry.sqlite3"))
    monkeypatch.delenv("BRAIN_EXECUTOR_ATTESTATION_SIGNING_KEY_B64", raising=False)
    monkeypatch.setenv("BRAIN_CLOUD_EXECUTOR_ENROLLMENTS_SHA256_JSON", "{}")
    monkeypatch.setenv("BRAIN_CLOUD_EXECUTOR_HOST_BINDINGS_JSON", "{}")

    result = attestation_status()

    assert result["status"] == "NOT_READY"
    assert result["control_plane_configured"] is False
    assert result["live_attestation_verified"] is False
