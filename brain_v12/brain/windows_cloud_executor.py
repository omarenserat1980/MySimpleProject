from __future__ import annotations

"""Provider-neutral contract for a real cloud Windows Server 2025 executor.

Provider credentials and infrastructure operations stay outside this module.
A concrete adapter must implement WindowsCloudProvider.
"""

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol


WINDOWS_SERVER_2025 = "Windows Server 2025"
WINDOWS_CLOUD = "windows-server-2025-cloud"


@dataclass(frozen=True)
class CloudWindowsVM:
    vm_id: str
    provider: str
    region: str
    state: str
    os: str = WINDOWS_SERVER_2025
    architecture: str = "x86_64"
    metadata: Mapping[str, Any] = field(default_factory=dict)


class WindowsCloudProvider(Protocol):
    name: str

    def provision_windows_server_2025(self, **kwargs: Any) -> CloudWindowsVM: ...
    def status(self, vm_id: str) -> CloudWindowsVM: ...
    def destroy(self, vm_id: str) -> None: ...


class WindowsCloudExecutor:
    capability = WINDOWS_CLOUD

    def __init__(self, provider: WindowsCloudProvider | None = None):
        self.provider = provider

    def readiness(self) -> dict[str, Any]:
        if self.provider is None:
            return {
                "status": "NOT_CONFIGURED",
                "ready": False,
                "executor": self.capability,
                "reason": "CLOUD_WINDOWS_PROVIDER_NOT_CONFIGURED",
            }
        return {
            "status": "CONFIGURED",
            "ready": True,
            "executor": self.capability,
            "provider": self.provider.name,
        }

    def provision(self, **kwargs: Any) -> CloudWindowsVM:
        if self.provider is None:
            raise RuntimeError("CLOUD_WINDOWS_PROVIDER_NOT_CONFIGURED")
        vm = self.provider.provision_windows_server_2025(**kwargs)
        self._validate(vm)
        return vm

    def status(self, vm_id: str) -> dict[str, Any]:
        if self.provider is None:
            return {
                "status": "NOT_CONFIGURED",
                "verified": False,
                "executor": self.capability,
                "reason": "CLOUD_WINDOWS_PROVIDER_NOT_CONFIGURED",
            }
        vm = self.provider.status(vm_id)
        return self.verify(vm)

    def verify(self, vm: CloudWindowsVM) -> dict[str, Any]:
        self._validate(vm)
        return {
            "status": "CLOUD_WINDOWS_VM_READY" if vm.state == "RUNNING" else "CLOUD_WINDOWS_VM_NOT_READY",
            "verified": vm.state == "RUNNING",
            "executor": self.capability,
            "provider": vm.provider,
            "vm_id": vm.vm_id,
            "region": vm.region,
            "os": vm.os,
            "architecture": vm.architecture,
        }

    @staticmethod
    def _validate(vm: CloudWindowsVM) -> None:
        if vm.os != WINDOWS_SERVER_2025:
            raise ValueError("CLOUD_GUEST_OS_NOT_WINDOWS_SERVER_2025")
        if vm.architecture.lower() not in {"x86_64", "amd64"}:
            raise ValueError("CLOUD_GUEST_ARCH_NOT_X86_64")
        if not vm.provider:
            raise ValueError("CLOUD_PROVIDER_REQUIRED")
        if not vm.vm_id:
            raise ValueError("CLOUD_VM_ID_REQUIRED")
