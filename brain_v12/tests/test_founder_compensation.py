from brain_v12.brain.founder_compensation import FounderCompensationPlanner

def test_blocks_without_destination():
    p = FounderCompensationPlanner()
    r = p.evaluate(100000, 20000, 30000, 10000, 1000)
    assert r["status"] == "BLOCKED"

def test_caps_cash_compensation():
    p = FounderCompensationPlanner(founder_share_limit=0.10)
    r = p.evaluate(100000, 20000, 30000, 10000, 4000,
                   destination_ref="verified-founder-destination",
                   approval_id="approval-1")
    assert r["status"] == "PAYMENT_AUTHORIZATION_READY"
    assert r["maximum_recommended"] == 4000.0


def test_blocks_when_proposed_amount_exceeds_safe_limit():
    p = FounderCompensationPlanner(founder_share_limit=0.10)
    r = p.evaluate(100000, 20000, 30000, 10000, 4001,
                   destination_ref="verified-founder-destination",
                   approval_id="approval-1")
    assert r["status"] == "BLOCKED"
    assert r["reason"] == "reserve_or_founder_share_limit"

def test_requires_approval_before_authorization():
    p = FounderCompensationPlanner()
    r = p.evaluate(100000, 20000, 30000, 10000, 4000,
                   destination_ref="verified-founder-destination")
    assert r["status"] == "APPROVAL_PENDING"

def test_never_treats_planning_as_verified_payment():
    p = FounderCompensationPlanner()
    r = p.evaluate(100000, 20000, 30000, 10000, 4000,
                   destination_ref="verified-founder-destination",
                   approval_id="approval-1")
    assert r["status"] == "PAYMENT_AUTHORIZATION_READY"
    assert r["status"] != "PAYMENT_VERIFIED"
