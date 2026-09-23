from brain_v7.braincore_v2.financial_risk_engine import score
from brain_v7.braincore_v2.payment_state_machine import transition
from brain_v7.braincore_v2.card_security import assess
from brain_v7.braincore_v2.security_monitor import correlate
from brain_v7.braincore_v2.compliance_engine import evaluate
from brain_v7.braincore_v2.financial_limits import check

def test_high_risk_requires_review():
    assert score(amount_jod=9000,velocity=9,device_change=8,geo_anomaly=8,beneficiary_new=8,chargeback_history=0)["requires_review"]

def test_invalid_payment_transition_is_rejected():
    try: transition("CONFIRMED","SUBMITTED"); assert False
    except ValueError: pass

def test_atm_tamper_is_critical():
    assert assess(pin_failures=0,atm_tamper_alert=True,offline_anomaly=False,unusual_withdrawal=False)["severity"]=="critical"

def test_security_correlation():
    assert correlate([{"type":"tamper","severity":"critical"}])["incident_required"]

def test_compliance_blocks_missing_evidence():
    assert evaluate({})["compliant"] is False

def test_financial_reserve_is_protected():
    assert check(80,0,100,100,50)["allowed"] is False
