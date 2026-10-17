from datetime import datetime, timedelta, timezone

from brain_v12.brain.cloud_capacity_gate import CapacityRequest, evaluate_free_capacity


NOW = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)


def evidence(**overrides):
    value = {
        "provider_verified": True,
        "provider": "example-provider",
        "region": "free-region-1",
        "sku": "free-small",
        "source_ref": "provider-quota-response:abc123",
        "observed_at": (NOW - timedelta(minutes=1)).isoformat(),
        "expires_at": (NOW + timedelta(minutes=10)).isoformat(),
        "free_tier_eligible": True,
        "estimated_monthly_cost_usd": "0.00",
        "available_vcpu": 2,
        "available_memory_mb": 4096,
        "available_storage_gb": 20,
    }
    value.update(overrides)
    return value


def test_fresh_verified_zero_cost_capacity_is_eligible():
    result = evaluate_free_capacity(CapacityRequest(1, 1024, 5), evidence(), now=NOW)
    assert result["status"] == "ELIGIBLE"
    assert result["provisioning_performed"] is False
    assert result["paid_fallback_allowed"] is False


def test_paid_capacity_is_blocked():
    result = evaluate_free_capacity(CapacityRequest(1, 1024), evidence(estimated_monthly_cost_usd="0.01"), now=NOW)
    assert result["status"] == "BLOCKED"
    assert "zero_cost_confirmed" in result["blocked_reasons"]


def test_unverified_or_stale_evidence_is_blocked():
    result = evaluate_free_capacity(
        CapacityRequest(1, 1024),
        evidence(provider_verified=False, expires_at=(NOW - timedelta(seconds=1)).isoformat()),
        now=NOW,
    )
    assert result["status"] == "BLOCKED"
    assert "provider_verified" in result["blocked_reasons"]
    assert "evidence_not_expired" in result["blocked_reasons"]


def test_insufficient_capacity_is_blocked():
    result = evaluate_free_capacity(
        CapacityRequest(2, 4096, 25),
        evidence(available_vcpu=1, available_memory_mb=2048, available_storage_gb=10),
        now=NOW,
    )
    assert result["status"] == "BLOCKED"
    assert {"vcpu_sufficient", "memory_sufficient", "storage_sufficient"} <= set(result["blocked_reasons"])


def test_invalid_request_is_rejected():
    try:
        CapacityRequest(0, 1024)
    except ValueError as exc:
        assert str(exc) == "CAPACITY_REQUEST_INVALID"
    else:
        raise AssertionError("invalid request was accepted")


def test_boolean_resource_counts_are_not_accepted_as_integers():
    result = evaluate_free_capacity(CapacityRequest(1, 1024), evidence(available_vcpu=True), now=NOW)
    assert result["status"] == "BLOCKED"
    assert "vcpu_sufficient" in result["blocked_reasons"]
