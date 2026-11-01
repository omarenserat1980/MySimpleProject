from brain_v12.vehicle_network.diagnostics import collect_readonly_diagnostics, record_diagnostics
from brain_v12.vehicle_network.memory import summary


def test_readonly_probe_returns_expected_shape(monkeypatch):
    from brain_v12.vehicle_network import diagnostics

    def fake_run(command):
        if command == ["getprop", "sys.usb.state"]:
            return "mtp,adb"
        if command == ["ip", "-brief", "link"]:
            return "lo UNKNOWN"
        return None

    monkeypatch.setattr(diagnostics, "_run", fake_run)
    result = collect_readonly_diagnostics()
    assert result["android_properties"]["sys.usb.state"] == "mtp,adb"
    assert result["network_interfaces"] == "lo UNKNOWN"
    assert result["routes"] is None
    assert result["limitations"]


def test_probe_persists_observation_without_changing_system(tmp_path):
    db_path = tmp_path / "brain.sqlite3"
    result = {
        "android_properties": {"sys.usb.state": "mtp,adb"},
        "network_interfaces": "lo UNKNOWN",
        "routes": None,
    }
    record_diagnostics(result, db_path)
    state = summary(db_path)
    assert state["primary_goal"]["status"] == "active"
