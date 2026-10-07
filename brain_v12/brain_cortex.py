"""Brain Cortex v1: shared cognitive policy primitives."""

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class CapabilityState(str, Enum):
    READY = "READY"
    DEGRADED = "DEGRADED"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class Capability:
    id: str
    name: str
    state: CapabilityState = CapabilityState.UNKNOWN
    detail: str = ""


@dataclass(frozen=True)
class Decision:
    action: str
    reason: str
    requires_permission: bool = False


class BrainCortex:
    CONSTITUTION = (
        "No sensitive action without an explicit permission gate.",
        "No success claim without verification evidence.",
        "Do not retry a failure blindly; diagnose first.",
        "Prefer one orchestrated execution path over competing loops.",
        "Keep recovery/rollback possible before system-changing operations.",
    )

    def decide(self, action: str, *, requires_permission: bool = False) -> Decision:
        return Decision(
            action=action,
            reason="Cortex policy: observe -> decide -> permission -> execute -> verify",
            requires_permission=requires_permission,
        )

    @staticmethod
    def health(capabilities: Iterable[Capability]) -> str:
        states = {c.state for c in capabilities}
        if CapabilityState.BLOCKED in states:
            return "BLOCKED"
        if CapabilityState.DEGRADED in states:
            return "DEGRADED"
        if CapabilityState.UNKNOWN in states:
            return "UNKNOWN"
        return "READY"
