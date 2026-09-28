from .code_repair_app import classify, run_repair


def test_classify_known_pytest_failure():
    result = classify("ModuleNotFoundError: No module named pytest\ncinematic-factory-smoke")
    assert result["failure_class"] == "workflow_dependency"
    assert result["repair_rule"] == "rule_cinematic_smoke_installs_pytest"
    assert result["safe_to_auto_repair"] is True


def test_classify_unknown_is_not_auto_repairable():
    result = classify("some completely unknown production failure")
    assert result["safe_to_auto_repair"] is False
    assert result["repair_rule"] == "none_allowlisted"


def test_repair_app_produces_safety_report(tmp_path):
    report = tmp_path / "repair.json"
    result = run_repair("", report_path=str(report))
    assert result["status"] == "CODE_VERIFIED"
    assert result["safety"]["allowlisted_repairs_only"] is True
    assert result["safety"]["rollback_on_failed_verification"] is True
    assert report.exists()
