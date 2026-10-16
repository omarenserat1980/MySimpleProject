from brain_v12.brain.digital_mining_node import inspect_node


def test_empty_environment_fails_closed_as_gateway_not_miner():
    result = inspect_node({})
    assert result["status"] == "BLOCKED"
    assert result["execution_mode"] == "GATEWAY_CONNECTIVITY_PREFLIGHT_ONLY"
    assert result["local_mining_allowed"] is False
    assert result["physical_device_computation_allowed"] is False
    assert result["real_mining_started"] is False
    assert "BRAIN_CONTROL_PLANE_URL_NOT_CONFIGURED" in result["blockers"]
    assert "GATEWAY_AUTH_TOKEN_NOT_CONFIGURED" in result["blockers"]
    assert "NOT_RUNNING_IN_TERMUX" not in result["blockers"]
    assert "TRUSTED_MINER_BINARY_NOT_FOUND" not in result["blockers"]


def test_gateway_does_not_need_local_miner_or_pool_settings():
    secret = "gateway-token-never-output"
    pool_url = "stratum+tcp://pool.example.invalid:3333"
    worker_name = "private-worker-identifier"
    brain_url = "https://brain.example.invalid"
    result = inspect_node({
        "V12_BRAIN_URL": brain_url,
        "BRAIN_AGENT_KEY": secret,
        "BRAIN_MINING_POOL_URL": pool_url,
        "BRAIN_MINING_WORKER": worker_name,
    })
    assert result["status"] == "GATEWAY_CONFIGURED_NOT_VERIFIED"
    assert result["gateway_configured"] is True
    assert result["gateway_identity_verified"] is False
    assert result["local_mining_allowed"] is False
    assert result["physical_device_computation_allowed"] is False
    assert result["pool_contacted"] is False
    serialized = str(result)
    for private_value in (secret, pool_url, worker_name, brain_url):
        assert private_value not in serialized


def test_pool_credentials_without_brain_gateway_config_are_not_enough():
    result = inspect_node({
        "BRAIN_MINING_POOL_URL": "stratum+tcp://pool.example.invalid:3333",
        "BRAIN_MINING_WORKER": "worker-name",
    })
    assert result["status"] == "BLOCKED"
    assert "BRAIN_CONTROL_PLANE_URL_NOT_CONFIGURED" in result["blockers"]
    assert "GATEWAY_AUTH_TOKEN_NOT_CONFIGURED" in result["blockers"]
