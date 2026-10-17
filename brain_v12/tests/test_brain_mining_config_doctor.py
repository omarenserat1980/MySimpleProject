from brain_v12.tools.brain_mining_config_doctor import audit_environment


def test_braiins_and_brain_worker_credentials_are_separate_domains():
    result = audit_environment({
        "BRAIINS_POOL_API_TOKEN": "pool-secret-do-not-print",
        "BRAIINS_POOL_WORKER_ID": "account.worker-01",
    })
    assert result["ready_for_braiins_readonly_telemetry"] is True
    assert result["ready_for_brain_worker_telemetry"] is False
    assert result["credential_domains_are_not_interchangeable"] is True
    assert result["credential_domains"]["brain_worker_telemetry_intake"]["variables"][
        "BRAIN_MINING_WORKER_API_TOKEN"
    ]["configured"] is False
    assert "pool-secret-do-not-print" not in str(result)


def test_worker_telemetry_requires_its_own_token_urls_and_worker_id():
    result = audit_environment({
        "BRAIN_MINING_WORKER_API_TOKEN": "x" * 40,
        "BRAIN_MINING_API_URL": "https://brain.example",
        "BRAIN_MINER_STATS_URL": "http://127.0.0.1:9000/stats",
        "BRAIN_MINING_WORKER_ID": "device.worker-01",
        "BRAIN_MINING_HEARTBEAT_SECONDS": "30",
    })
    assert result["ready_for_brain_worker_telemetry"] is True
    assert result["ready_for_braiins_readonly_telemetry"] is False
    assert result["secret_values_printed"] is False
    assert result["network_accessed"] is False
    assert result["miner_started"] is False
    assert result["accepted_shares_verified"] is False
    assert "x" * 40 not in str(result)


def test_invalid_worker_id_and_heartbeat_fail_closed():
    result = audit_environment({
        "BRAIN_MINING_WORKER_API_TOKEN": "x" * 40,
        "BRAIN_MINING_API_URL": "https://brain.example",
        "BRAIN_MINER_STATS_URL": "http://127.0.0.1:9000/stats",
        "BRAIN_MINING_WORKER_ID": "../bad",
        "BRAIN_MINING_HEARTBEAT_SECONDS": "2",
    })
    assert result["ready_for_brain_worker_telemetry"] is False
    assert result["credential_domains"]["worker_connectivity"]["worker_id_format_valid"] is False
    assert result["optional_configuration"]["BRAIN_MINING_HEARTBEAT_SECONDS"]["policy_satisfied"] is False


def test_empty_environment_is_blocked_without_side_effects():
    result = audit_environment({})
    assert result["ready_for_braiins_readonly_telemetry"] is False
    assert result["ready_for_brain_worker_telemetry"] is False
    assert result["secret_files_read"] is False
    assert result["network_accessed"] is False
    assert result["pool_settings_changed"] is False
    assert result["revenue_verified"] is False
