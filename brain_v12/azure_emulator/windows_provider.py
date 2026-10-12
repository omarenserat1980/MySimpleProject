from __future__ import annotations
from .service import AzureEmulator
from brain_v12.brain.windows_cloud_executor import CloudWindowsVM, WindowsCloudProvider

class EmulatorWindowsProvider:
    name = "brain-emulated-azure"
    def __init__(self, cloud: AzureEmulator | None = None):
        self.cloud = cloud or AzureEmulator(free_only=True)
    def provision_windows_server_2025(self, **kwargs) -> CloudWindowsVM:
        name = kwargs.get("name", "brain-win2025")
        vm = self.cloud.create_windows_server_2025_vm(
            name, vcpus=int(kwargs.get("vcpus",2)),
            memory_mb=int(kwargs.get("memory_mb",4096)),
            storage_gb=int(kwargs.get("storage_gb",64)),
            nic=str(kwargs.get("nic","brain-nic")),
        )
        return self._map(vm)
    def status(self, vm_id: str) -> CloudWindowsVM:
        r=self.cloud.resources.get(vm_id)
        if r is None: raise KeyError(vm_id)
        return self._map(r)
    def destroy(self, vm_id: str) -> None:
        r=self.cloud.resources.get(vm_id)
        if r is None: raise KeyError(vm_id)
        r.state="DELETED"
    @staticmethod
    def _map(r):
        return CloudWindowsVM(r.id,"brain-emulated-azure","emulated",r.state,
                              os=str(r.properties.get("os","Windows Server 2025")),
                              architecture=str(r.properties.get("architecture","x86_64")),
                              metadata=dict(r.properties))

