from brain_v12.azure_emulator.service import AzureEmulator
from brain_v12.azure_emulator.windows_provider import EmulatorWindowsProvider
from brain_v12.brain.windows_cloud_executor import WindowsCloudExecutor

def test_emulator_provider_provisions_through_executor():
    cloud=AzureEmulator(free_only=True)
    provider=EmulatorWindowsProvider(cloud)
    ex=WindowsCloudExecutor(provider)
    vm=ex.provision(name="brain-win2025",vcpus=2,memory_mb=4096,storage_gb=64)
    result=ex.verify(vm)
    assert result["verified"] is True
    assert result["provider"]=="brain-emulated-azure"
    assert result["os"]=="Windows Server 2025"

def test_emulator_provider_respects_free_capacity():
    cloud=AzureEmulator(free_only=True,quota={"vcpus":2,"memory_mb":4096,"storage_gb":64})
    ex=WindowsCloudExecutor(EmulatorWindowsProvider(cloud))
    ex.provision(name="first",vcpus=2,memory_mb=4096,storage_gb=64)
    try:
        ex.provision(name="second",vcpus=1,memory_mb=1024,storage_gb=32)
    except RuntimeError as e:
        assert str(e)=="CAPACITY_GATE_FAILED:vcpus,memory_mb,storage_gb"
    else:
        raise AssertionError("capacity gate bypassed")

def test_runtime_requires_guest_heartbeat():
    cloud=AzureEmulator(free_only=True)
    ex=WindowsCloudExecutor(EmulatorWindowsProvider(cloud))
    vm=ex.provision()
    now=2000.0
    node={"node_id":vm.vm_id,"provider":vm.provider,"state":"RUNNING","architecture":"x86_64",
          "last_heartbeat":now-1,
          "capabilities":["windows-server-2025","windows-cloud","brain-heartbeat"]}
    assert ex.verify_runtime(vm,node,now=now)["runtime_verified"] is True
