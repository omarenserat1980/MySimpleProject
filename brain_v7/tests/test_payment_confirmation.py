from brain_v7.braincore_v2.payment_confirmation import reconcile_confirmation

class R:
    def __init__(self,status,ref,amount): self.status=status; self.provider_reference=ref; self.amount_jod=amount

def test_confirmed_amount_matches():
    r=reconcile_confirmation(requested_amount_jod=25,provider_reference="P1",provider_result=R("CONFIRMED","P1",25))
    assert r.status=="CONFIRMED"

def test_mismatch_fails_closed():
    r=reconcile_confirmation(requested_amount_jod=25,provider_reference="P1",provider_result=R("CONFIRMED","P1",24))
    assert r.status=="FAILED"

def test_pending_is_not_success():
    r=reconcile_confirmation(requested_amount_jod=25,provider_reference="P1",provider_result=R("PENDING","P1",25))
    assert r.status=="PENDING"
