from brain_v7.braincore_v2.financial_cyber_domains import capability_map,action_allowed

def test_financial_and_security_domains_exist():
    names={x["name"] for x in capability_map()}
    assert {"banking_systems","payment_rails","card_processing","atm_security",
            "fraud_detection","defensive_security"} <= names

def test_unauthorized_financial_hacking_is_blocked():
    assert action_allowed("steal_credentials") is False
    assert action_allowed("clone_card") is False
    assert action_allowed("unauthorized_bank_access") is False
