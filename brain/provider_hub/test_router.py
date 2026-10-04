from brain.provider_hub.router import Provider, ProviderRouter

def test_choose_prefers_verified_priority():
    r=ProviderRouter([
        Provider("slow","ACTIVE",20,("checkout",)),
        Provider("best","VERIFIED",10,("checkout",)),
    ])
    assert r.choose("checkout").id=="best"

def test_failover_excludes_failed_provider():
    r=ProviderRouter([
        Provider("a","ACTIVE",10,("api",)),
        Provider("b","VERIFIED",20,("api",)),
    ])
    assert [p.id for p in r.failover_order("api","a")]==["b"]

def test_payment_guard_requires_evidence():
    try:
        ProviderRouter.payment_guard(
            order_id="BRAIN-MKT-1",
            payment_state="PAYMENT_VERIFIED",
            provider_reference="ref",
            verified_evidence=None,
        )
    except ValueError as e:
        assert str(e)=="PAYMENT_VERIFIED_REQUIRES_EVIDENCE"
    else:
        raise AssertionError("guard failed")
