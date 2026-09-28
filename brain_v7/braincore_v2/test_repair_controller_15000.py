from brain_v7.braincore_v2.repair_controller_15000 import MAX_CONTROLLER_CYCLES, controller

def test_controller_limit_is_15000():
    assert MAX_CONTROLLER_CYCLES == 15000

def test_controller_accepts_smaller_test_limit(tmp_path, monkeypatch):
    monkeypatch.setenv("FACTORY_LAST_ERROR", "")
    result = controller("", max_cycles=1, report_path=str(tmp_path / "report.json"))
    assert result["cycles_completed"] == 1
    assert result["status"] in {"VERIFIED_SUCCESS", "NO_ALLOWLISTED_REPAIR", "CONTROLLER_LIMIT_REACHED"}
