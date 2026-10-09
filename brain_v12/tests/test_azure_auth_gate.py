from brain_v12.brain.azure_auth_gate import check_azure_auth_readiness


def test_azure_auth_is_fail_closed_when_missing():
    result = check_azure_auth_readiness({}, cli_ready=False)
    assert result["ok"] is False
    assert result["status"] == "NOT_READY"
    assert "ARM_CLIENT_SECRET" in result["missing"]
    assert all(item["value_exposed"] is False for item in result["checks"])


def test_azure_auth_reports_ready_without_exposing_values():
    env = {
        "ARM_CLIENT_ID": "client-id",
        "ARM_TENANT_ID": "tenant-id",
        "ARM_SUBSCRIPTION_ID": "subscription-id",
        "ARM_CLIENT_SECRET": "secret",
    }
    result = check_azure_auth_readiness(env, cli_ready=False)
    assert result["ok"] is True
    assert result["status"] == "READY"
    assert result["missing"] == []
    assert "service_principal_env" in result["available_mechanisms"]
    assert all("value" not in item for item in result["checks"])
    assert all(item["value_exposed"] is False for item in result["checks"])


def test_azure_cli_is_an_accepted_runtime_identity():
    result = check_azure_auth_readiness({}, cli_ready=True)
    assert result["ok"] is True
    assert result["status"] == "READY"
    assert result["mechanism"] == "azure_cli"
    assert result["available_mechanisms"] == ["azure_cli"]
    assert all(item["value_exposed"] is False for item in result["checks"])


def test_workload_identity_is_an_accepted_runtime_identity():
    result = check_azure_auth_readiness(
        {"AZURE_FEDERATED_TOKEN_FILE": "/run/secrets/azure-token"},
        cli_ready=False,
    )
    assert result["ok"] is True
    assert result["status"] == "READY"
    assert result["mechanism"] == "workload_identity"
