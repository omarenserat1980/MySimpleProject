from brain_v12.brain.synthetic_customer import SyntheticCustomer, Proposal

def test_customer_requires_approval_and_merges_advisors():
    c=SyntheticCustomer()
    run=c.start("TEST_CUSTOMER_COMPANY","Build a company website with a service request form.")
    p=c.merge_proposals(
        Proposal("CHATGPT","UX plan",["website","responsive_ui"],["scope"],["pages","form"]),
        Proposal("BRAIN","Execution plan",["website","api"],["deployment"],["http","form"]),
    )
    assert p["approval_required"] is True
    assert set(p["sources"])=={"CHATGPT","BRAIN"}
    assert not run.approved
    c.approve(run,p)
    assert run.status=="APPROVED_FOR_TEST_EXECUTION"

def test_payment_gate_fails_closed():
    c=SyntheticCustomer()
    assert c.safety_gate("SANDBOX","TEST")["allowed"]
    assert not c.safety_gate("PRODUCTION","TEST")["allowed"]
    assert not c.safety_gate("SANDBOX","PRODUCTION")["allowed"]
