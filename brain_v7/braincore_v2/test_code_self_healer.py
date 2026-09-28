from .code_self_healer import MAX_CYCLES, SOURCE_ALLOWLIST, heal

def test_self_healer_has_bounded_cycles():
    assert MAX_CYCLES == 100
    assert all("MySimpleProject" in str(p) for p in SOURCE_ALLOWLIST)

def test_self_healer_verifies_current_workspace(tmp_path, monkeypatch):
    report = tmp_path / "healer.json"
    result = heal("", str(report))
    assert result["status"] == "CODE_VERIFIED"
    assert 1 <= result["cycles_completed"] <= 100
    assert report.exists()
