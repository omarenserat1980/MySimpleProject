from brain_v7.braincore_v2.unified_economic_brain import assess_financial_state
from brain_v7.braincore_v2.payment_provider_selector import ProviderSnapshot

def provider():
    return [ProviderSnapshot("wallet", True, True, True, True, 500, 200, 500, "HEALTHY")]

def test_unknown_cash_never_claims_ready():
    r = assess_financial_state(
        cash_jod=None, verified_profit_jod=0, candidate_expected_jod=100,
        risk_clear=True, transfer_amount_jod=100, providers=provider(),
        destination_ref="verified",
    )
    assert r.status == "NOT_READY"

def test_risk_blocks():
    r = assess_financial_state(
        cash_jod=500, verified_profit_jod=0, candidate_expected_jod=100,
        risk_clear=False, transfer_amount_jod=100, providers=provider(),
        destination_ref="verified",
    )
    assert r.status == "REVIEW_REQUIRED"

def test_ready_still_requires_authorized_execution():
    r = assess_financial_state(
        cash_jod=500, verified_profit_jod=0, candidate_expected_jod=100,
        risk_clear=True, transfer_amount_jod=100, providers=provider(),
        destination_ref="verified",
    )
    assert r.status == "READY_FOR_AUTHORIZED_EXECUTION"
    assert r.action == "PREPARE_TRANSFER"
