from brain_v12.azure_emulator.launch import build_and_verify
from brain_v12.azure_emulator.service import AzureEmulator


def test_launch_returns_verified_simulated_windows_environment():
    result = build_and_verify()
    assert result["ok"] is True
    evidence = result["evidence"]
    assert evidence["ok"] is True
    assert evidence["provider"] == "brain-emulated-azure"
    assert evidence["provenance"] == "SIMULATED"
    assert evidence["vm"]["state"] == "RUNNING"
    assert evidence["vm"]["properties"]["os"] == "Windows Server 2025"
    assert evidence["vm"]["properties"]["architecture"] == "x86_64"
    assert evidence["usage"] == {"vcpus": 2, "memory_mb": 4096, "storage_gb": 64}


def test_duplicate_resource_is_rejected_deterministically():
    cloud = AzureEmulator()
    cloud.create_resource_group("same-name")
    try:
        cloud.create_resource_group("same-name")
    except ValueError as exc:
        assert "resource already exists" in str(exc)
    else:
        raise AssertionError("duplicate resource was accepted")


def test_health_evidence_for_missing_vm_is_failed_and_simulated():
    cloud = AzureEmulator()
    evidence = cloud.health_evidence("missing-vm")
    assert evidence["ok"] is False
    assert evidence["vm"] is None
    assert evidence["provenance"] == "SIMULATED"


def test_capacity_gate_blocks_vm_without_allocating_resource():
    cloud = AzureEmulator(
        free_only=True,
        quota={"vcpus": 1, "memory_mb": 1024, "storage_gb": 16},
    )
    try:
        cloud.create_windows_server_2025_vm(
            "over-limit", vcpus=2, memory_mb=2048, storage_gb=32
        )
    except RuntimeError as exc:
        assert str(exc).startswith("CAPACITY_GATE_FAILED:")
    else:
        raise AssertionError("over-quota VM was accepted")
    assert not any(r.kind == "vm" for r in cloud.resources.values())
