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
