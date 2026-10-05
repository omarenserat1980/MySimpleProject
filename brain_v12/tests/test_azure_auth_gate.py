from brain_v12.brain.azure_auth_gate import check_azure_auth_readiness


def test_azure_auth_is_fail_closed_when_missing():
    result = check_azure_auth_readiness({})
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
    result = check_azure_auth_readiness(env)
    assert result["ok"] is True
    assert result["status"] == "READY"
    assert result["missing"] == []
    assert all("value" not in item for item in result["checks"])
    assert all(item["value_exposed"] is False for item in result["checks"])
