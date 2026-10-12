from brain_v12.azure_emulator.service import AzureEmulator

def test_windows_server_2025_launch_is_verified():
    cloud = AzureEmulator()
    cloud.create_resource_group("rg")
    cloud.create_network("vnet")
    cloud.create_subnet("subnet", "vnet")
    cloud.create_public_ip("ip")
    cloud.create_nic("nic", "subnet", "ip")
    cloud.create_disk("disk", 64)
    cloud.create_windows_server_2025_vm("vm", nic="nic")
    evidence = cloud.health_evidence("vm")
    assert evidence["ok"] is True
    assert evidence["vm"]["properties"]["os"] == "Windows Server 2025"

def test_free_capacity_gate_blocks_over_quota():
    cloud = AzureEmulator(free_only=True, quota={"vcpus": 1, "memory_mb": 1024, "storage_gb": 16})
    try:
        cloud.create_windows_server_2025_vm("too-large", vcpus=2, memory_mb=2048, storage_gb=32)
    except RuntimeError as exc:
        assert str(exc).startswith("CAPACITY_GATE_FAILED:")
    else:
        raise AssertionError("quota gate did not block deployment")
