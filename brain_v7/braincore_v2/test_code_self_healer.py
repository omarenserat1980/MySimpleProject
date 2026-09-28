from .code_self_healer import MAX_CYCLES, ROOT, SOURCE_ALLOWLIST, heal

def test_self_healer_has_bounded_cycles():
    assert MAX_CYCLES == 100
    assert all(ROOT in p.parents for p in SOURCE_ALLOWLIST)

def test_self_healer_verifies_current_workspace(tmp_path):
    report = tmp_path / "healer.json"
    result = heal("", str(report))
    assert result["status"] == "CODE_VERIFIED"
    assert 1 <= result["cycles_completed"] <= 100
    assert report.exists()
    assert result["history"][-1]["verification_passed"] is True
