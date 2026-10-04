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
