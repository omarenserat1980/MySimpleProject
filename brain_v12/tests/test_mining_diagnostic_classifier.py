from __future__ import annotations

from brain_v12.brain.mining_diagnostic_classifier import classify_mining_runtime_diagnosis


def test_missing_or_non_dict_evidence_fails_closed():
    report = classify_mining_runtime_diagnosis(None)
    assert report["diagnosis"] == "INSUFFICIENT_EVIDENCE"
    assert report["real_mining_verified"] is False
    assert report["revenue_verified"] is False
    assert report["network_access_performed"] is False


def test_dns_failure_is_classified_without_running_a_probe():
    report = classify_mining_runtime_diagnosis({"dns": "FAIL"})
    assert report["diagnosis"] == "DNS_RESOLUTION_FAILURE"
    assert report["network_access_performed"] is False
    assert report["credentials_read"] is False


def test_tcp_tls_and_stratum_failures_are_distinguished():
    cases = [
        ({"dns": "PASS", "tcp": "FAIL"}, "POOL_TCP_CONNECTION_FAILURE"),
        ({"dns": "PASS", "tcp": "PASS", "tls": "FAIL"}, "TLS_HANDSHAKE_FAILURE"),
        ({"dns": "PASS", "tcp": "PASS", "tls": "PASS", "stratum": "FAIL"}, "STRATUM_HANDSHAKE_FAILURE"),
    ]
    for evidence, expected in cases:
        assert classify_mining_runtime_diagnosis(evidence)["diagnosis"] == expected


def test_authorization_rejection_and_account_mismatch_are_distinct():
    assert classify_mining_runtime_diagnosis({"authorization": "REJECTED"})["diagnosis"] == "AUTHORIZATION_OR_WORKER_REJECTED"
    assert classify_mining_runtime_diagnosis({"account_match": "MISMATCH"})["diagnosis"] == "POOL_ACCOUNT_MISMATCH"


def test_connected_without_reported_shares_is_not_success():
    report = classify_mining_runtime_diagnosis({
        "dns": "PASS", "tcp": "PASS", "tls": "PASS", "stratum": "PASS",
        "authorization": "ACCEPTED", "accepted_shares": "NONE_REPORTED",
    })
    assert report["diagnosis"] == "CONNECTED_BUT_NO_ACCEPTED_SHARES_REPORTED"
    assert report["real_mining_verified"] is False
    assert report["brain_work_attribution_verified"] is False


def test_reported_accepted_shares_do_not_become_verified_mining_or_revenue():
    report = classify_mining_runtime_diagnosis({"accepted_shares": "ACCEPTED_REPORTED"})
    assert report["diagnosis"] == "POOL_ACCEPTED_SHARES_REPORTED"
    assert report["real_mining_verified"] is False
    assert report["revenue_verified"] is False


def test_no_local_process_does_not_rule_out_external_asic():
    report = classify_mining_runtime_diagnosis({"process_inventory": "NONE_FOUND"})
    assert report["diagnosis"] == "NO_KNOWN_HOST_MINER_PROCESS"
    assert any("external ASIC" in item for item in report["limitations"])


def test_unknown_values_are_not_trusted():
    report = classify_mining_runtime_diagnosis({
        "dns": "PASS", "tcp": "PASS", "tls": "PASS", "stratum": "PASS",
        "authorization": "ACCEPTED", "accepted_shares": "YES",
    })
    assert report["observations"]["accepted_shares"] == "UNKNOWN"
    assert report["diagnosis"] == "INSUFFICIENT_EVIDENCE"


def test_all_reports_preserve_safety_boundary():
    for evidence in (
        None,
        {"dns": "FAIL"},
        {"process_inventory": "NONE_FOUND"},
        {"accepted_shares": "ACCEPTED_REPORTED"},
    ):
        report = classify_mining_runtime_diagnosis(evidence)
        assert report["read_only_classifier"] is True
        assert report["network_access_performed"] is False
        assert report["credentials_read"] is False
        assert report["settings_changed"] is False
        assert report["miner_started_or_stopped"] is False
        assert report["real_mining_verified"] is False
        assert report["revenue_verified"] is False



def test_unrecognized_input_fields_and_secret_like_values_are_never_echoed():
    marker = "do-not-echo-secret-marker"
    report = classify_mining_runtime_diagnosis({
        "dns": "FAIL",
        "password": marker,
        "token": marker,
        "authorization_payload": marker,
        "raw_response": marker,
        "pool_url": "stratum+tcp://example.invalid:3333",
        "accepted_shares": {"count": 999, "verified": True},
    })
    serialized = str(report)
    assert marker not in serialized
    assert "stratum+tcp://" not in serialized
    assert report["diagnosis"] == "DNS_RESOLUTION_FAILURE"
    assert report["observations"]["accepted_shares"] == "UNKNOWN"
    assert report["real_mining_verified"] is False
    assert report["revenue_verified"] is False


def test_concrete_transport_failure_takes_precedence_over_reported_share_claim():
    report = classify_mining_runtime_diagnosis({
        "dns": "FAIL",
        "accepted_shares": "ACCEPTED_REPORTED",
    })
    assert report["diagnosis"] == "DNS_RESOLUTION_FAILURE"
    assert report["real_mining_verified"] is False
    assert report["brain_work_attribution_verified"] is False
    assert report["revenue_verified"] is False


def test_enum_values_are_exact_and_case_sensitive():
    report = classify_mining_runtime_diagnosis({
        "dns": "fail",
        "tcp": " PASS ",
        "tls": True,
        "stratum": 1,
        "authorization": "accepted",
        "accepted_shares": "accepted_reported",
        "account_match": "match",
        "process_inventory": "none_found",
    })
    assert report["diagnosis"] == "INSUFFICIENT_EVIDENCE"
    assert report["observations"]["connection_stages"] == {
        "dns": "UNKNOWN",
        "tcp": "UNKNOWN",
        "tls": "UNKNOWN",
        "stratum": "UNKNOWN",
    }
    assert report["observations"]["accepted_shares"] == "UNKNOWN"
    assert report["observations"]["process_inventory"] == "UNKNOWN"
