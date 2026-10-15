from brain_v12.brain.asic_self_modification_gate import evaluate_asic_change


def passed_checks():
    return {"unit": "passed", "rtl": "passed", "synthesis": "passed", "security": "passed"}


def test_valid_asic_branch_is_only_ready_for_review():
    result = evaluate_asic_change(
        candidate_branch="brain/asic-improvement",
        changed_paths=["brain_v12/asic/rtl/brain_asic_core.sv", "brain_v12/tests/test_asic.py"],
        checks=passed_checks(),
    )
    assert result["decision"] == "READY_FOR_REVIEW"
    assert result["deployment_authorized"] is False
    assert result["real_mining_verified"] is False


def test_main_branch_is_rejected():
    result = evaluate_asic_change(
        candidate_branch="main",
        changed_paths=["brain_v12/asic/rtl/brain_asic_core.sv"],
        checks=passed_checks(),
    )
    assert result["decision"] == "REJECT"
    assert "DIRECT_MAIN_MODIFICATION_FORBIDDEN" in result["reasons"]


def test_missing_or_blocked_tool_check_is_not_a_pass():
    result = evaluate_asic_change(
        candidate_branch="brain/asic-change",
        changed_paths=["brain_v12/asic/rtl/brain_asic_core.sv"],
        checks={"unit": "passed", "rtl": "blocked_tool_missing", "synthesis": "passed", "security": "passed"},
    )
    assert result["decision"] == "REJECT"
    assert "CHECK_RTL_BLOCKED_TOOL_MISSING" in result["reasons"]


def test_sensitive_or_out_of_scope_paths_are_rejected():
    result = evaluate_asic_change(
        candidate_branch="brain/asic-change",
        changed_paths=[".env", "brain_v12/brain/mining_node_api.py", "../outside.txt"],
        checks=passed_checks(),
    )
    assert result["decision"] == "REJECT"
    assert "SENSITIVE_PATH_FORBIDDEN" in result["reasons"]
    assert "PATH_OUTSIDE_INITIAL_ASIC_ALLOWLIST" in result["reasons"]
    assert "PATH_TRAVERSAL_OR_ABSOLUTE_PATH" in result["reasons"]


def test_failed_security_check_rejects_change():
    checks = passed_checks()
    checks["security"] = "failed"
    result = evaluate_asic_change(
        candidate_branch="brain/asic-change",
        changed_paths=["brain_v12/asic/rtl/brain_asic_core.sv"],
        checks=checks,
    )
    assert result["decision"] == "REJECT"
    assert "CHECK_SECURITY_FAILED" in result["reasons"]
