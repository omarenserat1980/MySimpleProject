from __future__ import annotations

from copy import deepcopy

from brain_v12.brain.mining_runtime_evidence_validator import (
    validate_mining_runtime_evidence,
)


def valid_envelope():
    return {
        "schema_version": 1,
        "evidence_id": "test-evidence-001",
        "source": {
            "kind": "authorized_host_collector",
            "collector_version": "0.1.0",
            "host_id": "test-host",
        },
        "observed_at": "2026-10-18T03:00:00Z",
        "collection": {
            "mode": "read_only",
            "network_probes_performed": False,
            "credentials_read": False,
            "settings_changed": False,
            "miner_started_or_stopped": False,
        },
        "observations": {
            "process_inventory": "UNKNOWN",
            "dns": "UNKNOWN",
            "tcp": "UNKNOWN",
            "tls": "UNKNOWN",
            "stratum": "UNKNOWN",
            "authorization": "UNKNOWN",
            "accepted_shares": "UNKNOWN",
            "account_match": "UNKNOWN",
        },
        "integrity": {
            "payload_sha256": "a" * 64,
            "signature": None,
            "signing_key_id": None,
        },
    }


def test_valid_envelope_is_only_structurally_valid_not_authenticated():
    report = validate_mining_runtime_evidence(valid_envelope())
    assert report["valid"] is True
    assert report["errors"] == []
    assert report["source_authenticated"] is False
    assert report["integrity_hash_verified"] is False
    assert report["real_mining_verified"] is False
    assert report["brain_work_attribution_verified"] is False
    assert report["revenue_verified"] is False
    assert report["network_access_performed"] is False


def test_non_object_and_wrong_schema_fail_closed():
    assert validate_mining_runtime_evidence(None)["valid"] is False
    evidence = valid_envelope()
    evidence["schema_version"] = 99
    report = validate_mining_runtime_evidence(evidence)
    assert report["valid"] is False
    assert "UNSUPPORTED_SCHEMA_VERSION" in report["errors"]


def test_missing_fields_and_bad_timestamp_are_rejected():
    evidence = valid_envelope()
    del evidence["source"]["host_id"]
    evidence["observed_at"] = "yesterday"
    report = validate_mining_runtime_evidence(evidence)
    assert report["valid"] is False
    assert "SOURCE_FIELDS_MISSING" in report["errors"]
    assert "OBSERVED_AT_MUST_BE_UTC_ISO8601" in report["errors"]


def test_unsafe_collection_flags_are_rejected():
    for flag in (
        "network_probes_performed",
        "credentials_read",
        "settings_changed",
        "miner_started_or_stopped",
    ):
        evidence = valid_envelope()
        evidence["collection"][flag] = True
        report = validate_mining_runtime_evidence(evidence)
        assert report["valid"] is False
        assert "UNSAFE_COLLECTION_FLAG:" + flag in report["errors"]


def test_invalid_observation_enum_and_bad_hash_are_rejected():
    evidence = valid_envelope()
    evidence["observations"]["tcp"] = "CONNECTED_MAYBE"
    evidence["integrity"]["payload_sha256"] = "not-a-hash"
    report = validate_mining_runtime_evidence(evidence)
    assert report["valid"] is False
    assert "INVALID_OBSERVATION:tcp" in report["errors"]
    assert "INTEGRITY_HASH_INVALID" in report["errors"]


def test_secret_like_fields_are_rejected():
    evidence = valid_envelope()
    evidence["observations"]["pool_password"] = "must-not-be-here"
    report = validate_mining_runtime_evidence(evidence)
    assert report["valid"] is False
    assert "FORBIDDEN_SECRET_LIKE_FIELD" in report["errors"]


def test_reported_shares_never_promote_real_mining_or_revenue():
    evidence = valid_envelope()
    evidence["observations"]["accepted_shares"] = "ACCEPTED_REPORTED"
    report = validate_mining_runtime_evidence(evidence)
    assert report["valid"] is True
    assert report["real_mining_verified"] is False
    assert report["brain_work_attribution_verified"] is False
    assert report["revenue_verified"] is False
