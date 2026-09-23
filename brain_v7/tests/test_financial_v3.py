from brain_v7.braincore_v2.fraud_rules import evaluate
from brain_v7.braincore_v2.reconciliation_engine import reconcile
from brain_v7.braincore_v2.audit_chain import append,verify
from brain_v7.braincore_v2.secret_boundary import reject_secret_like
from brain_v7.braincore_v2.circuit_breaker import CircuitBreaker
from brain_v7.braincore_v2.beneficiary_registry import add,can_pay

def test_fraud_rules_explain_flags():
    r=evaluate({"new_beneficiary":True,"amount_jod":600,"velocity_1h":6})
    assert "new_beneficiary_large_amount" in r["flags"]

def test_reconciliation_detects_mismatch():
    assert reconcile({"amount_jod":10,"currency":"JOD","provider_reference":"x"},
                     {"amount_jod":11,"currency":"JOD","provider_reference":"x"})["matched"] is False

def test_audit_chain_is_tamper_evident():
    c=[]; append(c,{"type":"payout","amount":10}); assert verify(c); c[0]["event"]["amount"]=11; assert not verify(c)

def test_secrets_rejected():
    try: reject_secret_like("api_key=abc"); assert False
    except ValueError: pass

def test_circuit_breaker_stops_repeated_failures():
    b=CircuitBreaker(True,2); b.record_failure(); b.record_failure(); assert b.can_submit() is False

def test_unverified_beneficiary_cannot_receive_payout():
    r=add({},"wallet",False); assert can_pay(r,"wallet") is False
    r=add(r,"wallet2",True); assert can_pay(r,"wallet2") is True
