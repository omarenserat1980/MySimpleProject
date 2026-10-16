import json

from brain_v12.tools import brain_mining_runtime_doctor as doctor


def test_matches_known_miner_names_case_insensitively_and_deduplicates():
    assert doctor._matches(["XMRig", "xmrig", "Windows PowerShell", "Braiins OS", ""]) == ["Braiins OS", "XMRig"]


def test_linux_inventory_is_read_only_and_does_not_claim_pool_evidence(monkeypatch):
    monkeypatch.setattr(doctor.shutil, "which", lambda _name: None)
    monkeypatch.setattr(doctor, "_run_readonly", lambda command, timeout=12: (0, "systemd\npython\n"))
    result = doctor.collect_diagnostics("linux")
    assert result["status"] == "NO_KNOWN_MINER_DETECTED"
    assert result["read_only"] is True
    assert result["settings_changed"] is False
    assert result["miner_started_or_stopped"] is False
    assert result["network_scan_performed"] is False
    assert result["secrets_read"] is False
    assert result["evidence_sources_available"]["processes"] is True
    assert result["evidence"]["process_candidates"] == []
    assert any("accepted shares" in item for item in result["limitations"])


def test_linux_inventory_reports_candidate_without_claiming_real_mining(monkeypatch):
    monkeypatch.setattr(doctor.shutil, "which", lambda name: "/usr/bin/xmrig" if name == "xmrig" else None)
    monkeypatch.setattr(doctor, "_run_readonly", lambda command, timeout=12: (0, "xmrig\n"))
    result = doctor.collect_diagnostics("linux")
    assert result["status"] == "MINER_CANDIDATE_DETECTED"
    assert result["evidence"]["process_candidates"] == ["xmrig"]
    assert result["evidence"]["miner_binaries_on_path"] == ["xmrig"]
    assert "real_mining_verified" not in result


def test_windows_inventory_handles_single_values_and_unavailable_sources(monkeypatch):
    monkeypatch.setattr(doctor.shutil, "which", lambda _name: None)
    monkeypatch.setattr(doctor, "_windows_inventory", lambda: (
        {"processes": ["xmrig"], "services": [], "tasks": [], "apps": []},
        {"processes": True, "services": False, "tasks": False, "apps": False},
    ))
    result = doctor.collect_diagnostics("windows")
    assert result["status"] == "MINER_CANDIDATE_DETECTED"
    assert result["evidence"]["process_candidates"] == ["xmrig"]
    assert result["evidence_sources_available"]["services"] is False
    assert result["settings_changed"] is False


def test_unknown_platform_reports_insufficient_capability(monkeypatch):
    monkeypatch.setattr(doctor.shutil, "which", lambda _name: None)
    result = doctor.collect_diagnostics("plan9")
    assert result["status"] == "INSUFFICIENT_DIAGNOSTIC_CAPABILITY"
    assert result["evidence_sources_available"]["processes"] is False


def test_cli_json_output_is_machine_readable(monkeypatch, capsys):
    monkeypatch.setattr(doctor, "collect_diagnostics", lambda: {"status": "NO_KNOWN_MINER_DETECTED", "read_only": True})
    monkeypatch.setattr("sys.argv", ["brain_mining_runtime_doctor.py", "--json"])
    assert doctor.main() == 0
    assert json.loads(capsys.readouterr().out)["read_only"] is True
