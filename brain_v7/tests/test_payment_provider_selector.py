from brain_v7.braincore_v2.payment_provider_selector import (
    ProviderSnapshot, choose_provider
)

def test_selects_only_healthy_configured_provider():
    snapshots = [
        ProviderSnapshot("disabled", False, True, True, True, 500, 200, 500, "HEALTHY"),
        ProviderSnapshot("no-auth", True, False, True, True, 500, 200, 500, "HEALTHY"),
        ProviderSnapshot("real-wallet", True, True, True, True, 150, 100, 150, "HEALTHY"),
    ]
    result = choose_provider(100, snapshots, "verified")
    assert result.status == "READY_FOR_PROVIDER_SELECTION"
    assert result.provider == "real-wallet"

def test_rejects_insufficient_funds():
    snapshots = [
        ProviderSnapshot("wallet", True, True, True, True, 50, 100, 500, "HEALTHY")
    ]
    result = choose_provider(100, snapshots, "verified")
    assert result.status == "NO_EXECUTABLE_PROVIDER"

def test_rejects_unhealthy_provider():
    snapshots = [
        ProviderSnapshot("wallet", True, True, True, True, 500, 100, 500, "DEGRADED")
    ]
    result = choose_provider(100, snapshots, "verified")
    assert result.status == "NO_EXECUTABLE_PROVIDER"

def test_never_claims_execution():
    snapshots = [
        ProviderSnapshot("wallet", True, True, True, True, 500, 100, 500, "HEALTHY")
    ]
    result = choose_provider(100, snapshots, "verified")
    assert result.status == "READY_FOR_PROVIDER_SELECTION"
    assert "TRANSFER" not in result.status
