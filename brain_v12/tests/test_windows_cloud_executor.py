from brain_v12.brain.windows_cloud_executor import (
    CloudWindowsVM,
    WindowsCloudExecutor,
    WINDOWS_CLOUD,
)


class FakeProvider:
    name = "test-cloud"

    def provision_windows_server_2025(self, **kwargs):
        return CloudWindowsVM(
            vm_id="test-vm-01",
            provider=self.name,
            region="test-region",
            state="RUNNING",
        )

    def status(self, vm_id):
        return CloudWindowsVM(vm_id, self.name, "test-region", "RUNNING")

    def destroy(self, vm_id):
        pass


def test_windows_cloud_executor_requires_real_cloud_identity():
    vm = CloudWindowsVM("vm-1", "azure", "eastus", "RUNNING")
    result = WindowsCloudExecutor(FakeProvider()).verify(vm)
    assert result["verified"] is True
    assert result["executor"] == WINDOWS_CLOUD
    assert result["provider"] == "azure"


def test_windows_cloud_executor_rejects_wrong_os():
    vm = CloudWindowsVM("vm-1", "azure", "eastus", "RUNNING", os="Linux")
    try:
        WindowsCloudExecutor(FakeProvider()).verify(vm)
    except ValueError as exc:
        assert str(exc) == "CLOUD_GUEST_OS_NOT_WINDOWS_SERVER_2025"
    else:
        raise AssertionError("wrong OS was accepted")


def test_windows_cloud_executor_rejects_missing_provider():
    vm = CloudWindowsVM("vm-1", "", "eastus", "RUNNING")
    try:
        WindowsCloudExecutor(FakeProvider()).verify(vm)
    except ValueError as exc:
        assert str(exc) == "CLOUD_PROVIDER_REQUIRED"
    else:
        raise AssertionError("missing provider was accepted")


def test_windows_cloud_executor_reports_unconfigured_without_provider():
    result = WindowsCloudExecutor().readiness()
    assert result["ready"] is False
    assert result["status"] == "NOT_CONFIGURED"
    assert result["reason"] == "CLOUD_WINDOWS_PROVIDER_NOT_CONFIGURED"


def test_windows_cloud_executor_requires_fresh_guest_heartbeat_for_runtime():
    now = 2_000.0
    vm = CloudWindowsVM("test-vm-01", "test-cloud", "test-region", "RUNNING")
    node = {
        "node_id": "test-vm-01",
        "provider": "test-cloud",
        "state": "RUNNING",
        "architecture": "x86_64",
        "last_heartbeat": now - 10,
        "capabilities": ["windows-server-2025", "windows-cloud", "brain-heartbeat"],
    }
    result = WindowsCloudExecutor(FakeProvider()).verify_runtime(
        vm, node, heartbeat_timeout=120, now=now
    )
    assert result["runtime_verified"] is True
    assert result["status"] == "WINDOWS_CLOUD_RUNTIME_VERIFIED"


def test_windows_cloud_executor_rejects_stale_guest_heartbeat():
    now = 2_000.0
    vm = CloudWindowsVM("test-vm-01", "test-cloud", "test-region", "RUNNING")
    node = {
        "node_id": "test-vm-01",
        "provider": "test-cloud",
        "state": "RUNNING",
        "architecture": "x86_64",
        "last_heartbeat": now - 121,
        "capabilities": ["windows-server-2025", "windows-cloud", "brain-heartbeat"],
    }
    result = WindowsCloudExecutor(FakeProvider()).verify_runtime(
        vm, node, heartbeat_timeout=120, now=now
    )
    assert result["runtime_verified"] is False
    assert result["reason"] == "WINDOWS_CLOUD_HEARTBEAT_STALE"
