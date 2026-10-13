from brain_v12.brain.windows_software_boot_gate import WindowsSoftwareBootGate

def base():
    return {
        "media": {"sha256": "abc"},
        "uefi": {"ready": True},
        "cpu": {"x86_64": True},
        "guest": {"os": "Windows Server 2025", "architecture": "x86_64", "boot_verified": True},
        "storage": {"filesystem": "NTFS"},
        "executor": {"verified": True},
        "accelerator": "tcg",
        "kvm_claimed": False,
        "boot_source": "windows-installed-disk",
    }

def test_accepts_verified_tcg_boot():
    result = WindowsSoftwareBootGate().verify(base())
    assert result["verified"] is True
    assert result["status"] == "WINDOWS_BOOT_SOFTWARE_EMULATED"

def test_rejects_kvm_claim():
    evidence = base()
    evidence["kvm_claimed"] = True
    result = WindowsSoftwareBootGate().verify(evidence)
    assert result["verified"] is False
    assert "KVM_CLAIM_FORBIDDEN_IN_SOFTWARE_BOOT" in result["reasons"]

def test_rejects_missing_guest_boot_proof():
    evidence = base()
    evidence["guest"]["boot_verified"] = False
    result = WindowsSoftwareBootGate().verify(evidence)
    assert result["verified"] is False
    assert "GUEST_BOOT_NOT_VERIFIED" in result["reasons"]
