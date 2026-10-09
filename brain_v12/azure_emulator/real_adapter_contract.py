"""Final boundary for the minimal real-Azure phase."""
from dataclasses import dataclass
from typing import Protocol

@dataclass(frozen=True)
class LaunchPlan:
    location: str
    vm_size: str
    os_image: str = "Windows Server 2025"
    free_only: bool = True

class RealCloudAdapter(Protocol):
    def preflight(self, plan: LaunchPlan) -> dict: ...
    def provision(self, plan: LaunchPlan) -> dict: ...
    def verify(self, plan: LaunchPlan) -> dict: ...
    def destroy(self, plan: LaunchPlan) -> dict: ...

class FreeOnlyGuard:
    @staticmethod
    def require_free(preflight: dict) -> None:
        if not preflight.get("ok"):
            raise RuntimeError("REAL_CLOUD_PREFLIGHT_FAILED")
        if not preflight.get("free_capacity"):
            raise RuntimeError("FREE_CAPACITY_NOT_CONFIRMED")
        if preflight.get("estimated_cost", 0) != 0:
            raise RuntimeError("PAID_RESOURCE_BLOCKED")
