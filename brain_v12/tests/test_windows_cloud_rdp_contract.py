from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_rdp_is_restricted_in_network_security_group():
    terraform = read("brain_v12/cloud/windows_terraform/main.tf")
    assert 'name                   = "AllowRDP"' in terraform
    assert 'destination_port_range = "3389"' in terraform
    assert 'source_address_prefix  = var.allowed_source_ip' in terraform


def test_guest_enables_rdp_with_restricted_firewall_rule():
    script = read("scripts/windows-cloud/configure-winrm.ps1")
    assert "fDenyTSConnections -Value 0" in script
    assert 'New-NetFirewallRule -DisplayName "Electronic Brain RDP"' in script
    assert "-LocalPort 3389 -RemoteAddress $AllowedSourceIp" in script


def test_final_verification_requires_rdp_and_winrm():
    script = read("scripts/windows-cloud/verify.ps1")
    assert 'destinationPortRange -ne "3389"' in script
    assert 'destinationPortRange -ne "5986"' in script
    assert "Get-NetTCPConnection -State Listen -LocalPort 3389" in script
    assert "GUEST_RDP_READY_CLIENT_TEST_REQUIRED" in script


def test_cloud_apply_requires_explicit_cost_review_and_suitable_default():
    workflow = read(".github/workflows/brain-windows-cloud-launch.yml")
    assert "cost_reviewed:" in workflow
    assert "default: false" in workflow
    assert "BLOCKED_COST_REVIEW" in workflow
    assert "Standard_B2s" in workflow


def test_cost_estimator_is_read_only_and_labels_exclusions():
    script = read("scripts/windows-cloud/estimate-cost.py")
    assert "resources_created_or_changed" in script
    assert "COMPUTE_ONLY" in script
    assert "subscription-specific free credits or free-service eligibility" in script
    assert "terraform apply" not in script.lower()
