import json
from datetime import datetime, timezone

import pytest

from brain_v12.brain.cloud_provider_adapter import AzureReadOnlyProviderAdapter

NOW = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)


def make_runner(payloads, calls):
    def runner(command, timeout):
        calls.append((list(command), timeout))
        key = tuple(command[1:3])
        value = payloads.get(key)
        if isinstance(value, Exception):
            return 1, "", str(value)
        return 0, json.dumps(value), ""
    return runner


def test_azure_adapter_collects_read_only_snapshot_and_keeps_cost_unknown():
    calls = []
    payloads = {
        ("account", "show"): {"id": "subscription-123"},
        ("vm", "list-usage"): [{"name": {"value": "cores"}, "currentValue": 2, "limit": 10}],
        ("vm", "list-skus"): [{"name": "Standard_B2s", "restrictions": []}],
    }
    adapter = AzureReadOnlyProviderAdapter(runner=make_runner(payloads, calls), now=lambda: NOW)
    result = adapter.inspect_region("westeurope", "Standard_B2s")
    assert result["account_verified"] is True
    assert result["provider"] == "azure"
    assert result["sku_found"] is True
    assert result["vcpu_quota_limit"] == 10
    assert result["vcpu_quota_used"] == 2
    assert result["estimated_monthly_cost_usd"] is None
    assert result["free_tier_eligible"] is None
    assert result["provisioning_performed"] is False
    assert all("create" not in command and "delete" not in command for command, _ in calls)


def test_provider_errors_do_not_claim_verification():
    calls = []
    payloads = {
        ("account", "show"): RuntimeError("not logged in"),
        ("vm", "list-usage"): [],
        ("vm", "list-skus"): [],
    }
    result = AzureReadOnlyProviderAdapter(
        runner=make_runner(payloads, calls), now=lambda: NOW
    ).inspect_region("westeurope", "Standard_B2s")
    assert result["account_verified"] is False
    assert result["provider_verified"] is False
    assert result["source_ref"] is None
    assert result["errors"]


def test_bad_region_or_sku_is_rejected():
    adapter = AzureReadOnlyProviderAdapter(runner=lambda *_: (0, "{}", ""))
    with pytest.raises(ValueError, match="PROVIDER_REGION_AND_SKU_REQUIRED"):
        adapter.inspect_region("", "Standard_B2s")
