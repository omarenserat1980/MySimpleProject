from brain_v7.braincore_v2.payout_gateway import create_payout,confirm_payout

def test_payout_requires_external_confirmation():
    r=create_payout(100,"user-wallet","requested payout")
    assert r["status"]=="APPROVAL_REQUIRED"
    assert r["provider_confirmation_required"] is True
    assert r["credentials_requested"] is False

def test_confirmation_needs_provider_reference():
    assert confirm_payout("TX-123")["status"]=="CONFIRMED"
