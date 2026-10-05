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


def test_execution_does_not_trust_ok_without_verification():
    c = SyntheticCustomer(executor=lambda *args: {"ok": True, "artifact": "test-result"})
    run = c.start("TEST_CUSTOMER_SOFTWARE", "Build a test utility.")
    c.generate_proposals(run, {})
    c.approve(run)
    c.execute(run, environment="SANDBOX", payment_mode="TEST")
    assert run.status == "EXECUTION_FAILED"
    assert run.execution["ok"] is False


def test_execution_requires_cognitive_completion_and_verification():
    result = {"ok": True, "cognitive": {
        "execution": {"status": "COMPLETED"},
        "verification": {"status": "VERIFIED"},
    }}
    c = SyntheticCustomer(executor=lambda *args: result)
    run = c.start("TEST_CUSTOMER_SOFTWARE", "Build a test utility.")
    c.generate_proposals(run, {})
    c.approve(run)
    c.execute(run, environment="SANDBOX", payment_mode="TEST")
    assert run.status == "VERIFIED"
    assert run.execution["ok"] is True
    assert any(e["event"] == "EXECUTION_VERIFIED" for e in run.evidence)


def test_execution_uses_explicit_verified_result_when_no_cognitive_trace():
    c = SyntheticCustomer(executor=lambda *args: {"ok": True, "verified": True, "artifact": "test-result"})
    run = c.start("TEST_CUSTOMER_SOFTWARE", "Build a test utility.")
    c.generate_proposals(run, {})
    c.approve(run)
    c.execute(run, environment="SANDBOX", payment_mode="TEST")
    assert run.status == "VERIFIED"


def test_payment_gate_fails_closed():
    c = SyntheticCustomer()
    assert c.safety_gate("SANDBOX", "TEST")["allowed"]
    assert not c.safety_gate("PRODUCTION", "TEST")["allowed"]
    assert not c.safety_gate("SANDBOX", "PRODUCTION")["allowed"]


def test_customer_acceptance_and_delivery_lifecycle():
    c = SyntheticCustomer(executor=lambda *args: {"ok": True, "verified": True})
    run = c.start("TEST_CUSTOMER_COMPANY", "Build a safe test service.")
    c.generate_proposals(run, {})
    c.approve(run)
    c.execute(run, environment="TEST", payment_mode="NONE")
    c.review(run, accepted=True, feedback="Meets acceptance criteria")
    assert run.status == "ACCEPTED"
    c.deliver(run)
    assert run.status == "DELIVERED"


def test_customer_revision_requires_review_state():
    c = SyntheticCustomer()
    run = c.start("TEST_CUSTOMER_COMPANY", "Build a safe test service.")
    c.generate_proposals(run, {})
    c.approve(run)
    try:
        c.revise(run, "Change the form")
        assert False, "revision should require a revision request"
    except ValueError as exc:
        assert str(exc) == "REVISION_NOT_REQUESTED"
