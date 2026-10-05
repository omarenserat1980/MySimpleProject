from brain_v12.brain.synthetic_customer import SyntheticCustomer, Proposal


def test_customer_requires_approval_and_merges_advisors():
    c = SyntheticCustomer()
    run = c.start("TEST_CUSTOMER_COMPANY", "Build a company website with a service request form.")
    proposals = c.generate_proposals(run, {"capabilities": {"website": True}})
    assert proposals["unified"]["approval_required"] is True
    assert set(proposals["unified"]["sources"]) == {"CHATGPT", "BRAIN"}
    assert not run.approved
    c.approve(run)
    assert run.status == "APPROVED_FOR_TEST_EXECUTION"


def test_execution_requires_customer_approval():
    c = SyntheticCustomer(executor=lambda *args: {"ok": True})
    run = c.start("TEST_CUSTOMER_COMPANY", "Build a test website.")
    try:
        c.execute(run)
        assert False, "execution should require approval"
    except ValueError as exc:
        assert str(exc) == "CUSTOMER_APPROVAL_REQUIRED"


def test_execution_uses_safe_environment_and_records_evidence():
    c = SyntheticCustomer(executor=lambda *args: {"ok": True, "artifact": "test-result"})
    run = c.start("TEST_CUSTOMER_SOFTWARE", "Build a test utility.")
    c.generate_proposals(run, {})
    c.approve(run)
    c.execute(run, environment="SANDBOX", payment_mode="TEST")
    assert run.status == "VERIFIED"
    assert run.execution["ok"] is True
    assert any(e["event"] == "EXECUTION_VERIFIED" for e in run.evidence)


def test_payment_gate_fails_closed():
    c = SyntheticCustomer()
    assert c.safety_gate("SANDBOX", "TEST")["allowed"]
    assert not c.safety_gate("PRODUCTION", "TEST")["allowed"]
    assert not c.safety_gate("SANDBOX", "PRODUCTION")["allowed"]
