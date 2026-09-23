from brain_v7.braincore_v2.payment_provider import MockPaymentProvider

def test_provider_adapter_never_claims_real_transfer():
    r=MockPaymentProvider().submit(100,"wallet","abc")
    assert r.status=="SIMULATED"
    assert r.provider_reference.startswith("SIM-")
