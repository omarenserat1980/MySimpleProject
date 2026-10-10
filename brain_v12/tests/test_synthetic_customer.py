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
        "status": "COMPLETED",
        "objective_verified": True,
        "execution": {"status": "COMPLETED"},
        "verification": {
            "status": "VERIFIED",
            "objective_verified": True,
            "objective_status": "COMPLETED",
        },
    }}
    c = SyntheticCustomer(executor=lambda *args: result)
    run = c.start("TEST_CUSTOMER_SOFTWARE", "Build a test utility.")
    c.generate_proposals(run, {})
    c.approve(run)
    c.execute(run, environment="SANDBOX", payment_mode="TEST")
    assert run.status == "VERIFIED"
    assert run.execution["ok"] is True
    assert any(e["event"] == "EXECUTION_VERIFIED" for e in run.evidence)


def test_execution_rejects_verified_step_when_objective_is_still_in_progress():
    result = {"ok": True, "verified": True, "cognitive": {
        "status": "IN_PROGRESS",
        "objective_verified": False,
        "execution": {"status": "COMPLETED"},
        "verification": {
            "status": "VERIFIED",
            "scope": "selected_action",
            "objective_verified": False,
            "objective_status": "IN_PROGRESS",
        },
    }}
    c = SyntheticCustomer(executor=lambda *args: result)
    run = c.start("TEST_CUSTOMER_SOFTWARE", "Finish the whole test objective.")
    c.generate_proposals(run, {})
    c.approve(run)
    c.execute(run, environment="SANDBOX", payment_mode="TEST")
    assert run.status == "EXECUTION_FAILED"
    assert run.execution["ok"] is False
    assert run.execution["attempts"][0]["verified"] is False


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


def test_customer_cannot_accept_failed_execution():
    c = SyntheticCustomer(executor=lambda *args: {"ok": False, "verified": False, "error": "objective incomplete"})
    run = c.start("TEST_CUSTOMER_SOFTWARE", "Complete a test objective.")
    c.generate_proposals(run, {})
    c.approve(run)
    c.execute(run, environment="TEST", payment_mode="NONE")
    assert run.status == "EXECUTION_FAILED"
    try:
        c.review(run, accepted=True, feedback="force accept")
        assert False, "failed execution must never be accepted"
    except ValueError as exc:
        assert str(exc) == "VERIFIED_EXECUTION_REQUIRED_FOR_ACCEPTANCE"


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


def test_customer_feedback_is_forwarded_to_brain_revision_path():
    calls = []

    def feedback(request, text, customer_type, run_id):
        calls.append((request, text, customer_type, run_id))
        return {"ok": True, "revision_planned": True}

    c = SyntheticCustomer(feedback_executor=feedback)
    run = c.start("TEST_CUSTOMER_MARKETING", "Create a test campaign.")
    c.generate_proposals(run, {})
    run.status = "VERIFIED"
    c.review(run, accepted=False, feedback="The campaign needs a stronger conversion path.")
    assert run.status == "REVISION_REQUESTED"
    assert len(calls) == 1
    c.revise(run, "Add a stronger conversion path.")
    assert run.status == "WAITING_CUSTOMER_APPROVAL"
    assert "Customer revision feedback" in run.request


def test_customer_can_request_bounded_brain_repair_before_final_verification():
    calls = {"execute": 0, "repair": 0}

    def execute(*args):
        calls["execute"] += 1
        if calls["execute"] == 1:
            return {"ok": False, "verified": False, "gap": "missing test interface"}
        return {"ok": True, "verified": True, "artifact": "repaired-test-interface"}

    def repair(*args):
        calls["repair"] += 1
        return {"ok": True, "verified": True, "action": "bounded-repair"}

    c = SyntheticCustomer(executor=execute, repair_executor=repair, max_repair_attempts=1)
    run = c.start("TEST_CUSTOMER_SOFTWARE", "Provide a test interface.")
    c.generate_proposals(run, {})
    c.approve(run)
    c.execute(run, environment="SANDBOX", payment_mode="TEST")
    assert run.status == "VERIFIED"
    assert calls == {"execute": 2, "repair": 1}
    assert any(e["event"] == "BRAIN_GAP_REPAIR_ATTEMPT" for e in run.evidence)


def test_customer_review_is_instance_method_and_accepts_verified_run():
    c = SyntheticCustomer(executor=lambda *args: {"ok": True, "verified": True})
    run = c.start("TEST_CUSTOMER_COMPANY", "Build a safe test service.")
    c.generate_proposals(run, {})
    c.approve(run)
    c.execute(run, environment="TEST", payment_mode="NONE")
    c.review(run, accepted=True, feedback="accepted")
    assert run.status == "ACCEPTED"


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


def test_scenario_suite_plans_multiple_customer_levels():
    from brain_v12.brain.synthetic_customer_suite import SyntheticCustomerScenarioSuite
    suite = SyntheticCustomerScenarioSuite(lambda: SyntheticCustomer())
    plan = suite.plan()
    assert plan["scenario_count"] >= 7
    assert plan["production_allowed"] is False
    assert set(plan["levels"]) == {1, 2, 3, 4, 5}


def test_scenario_suite_runs_proposal_discovery_without_execution():
    from brain_v12.brain.synthetic_customer_suite import SyntheticCustomerScenarioSuite
    suite = SyntheticCustomerScenarioSuite(lambda: SyntheticCustomer())
    result = suite.run({"capabilities": {"website": True}, "tools": ["test"]}, limit=2)
    assert result["ok"] is True
    assert result["count"] == 2
    assert all(item["proposal_ready"] for item in result["results"])
