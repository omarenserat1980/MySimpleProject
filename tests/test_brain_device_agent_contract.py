from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_agent_v2_is_outbound_only():
    text=(ROOT/"brain_emulator_agent/brain_device_agent_v2.py").read_text(encoding="utf-8")
    assert "/api/device/heartbeat" in text
    assert "/api/device/poll" in text
    assert "/api/device/report" in text
    assert "HTTPServer" not in text
    assert "socketserver" not in text
def test_termux_boot_installer():
    text=(ROOT/"brain_emulator_agent/install_termux_agent.sh").read_text(encoding="utf-8")
    assert "termux-wake-lock" in text
    assert ".termux/boot" in text
    assert "brain_device_agent_v2.py" in text
def test_windows_installer():
    text=(ROOT/"brain_emulator_agent/install_windows_agent.ps1").read_text(encoding="utf-8")
    assert "brain_device_agent_v2.py" in text
    assert "arkan-01" in text
