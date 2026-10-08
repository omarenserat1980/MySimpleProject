from __future__ import annotations

"""Fail-closed executor routing for Brain runtime capabilities.

Routing selects a capability-specific executor contract; it never treats CI
success as runtime health and never creates parallel execution paths.
"""

from dataclasses import dataclass
from typing import Any, Mapping

from .execution_policy import (
    WINDOWS_CLOUD_NATIVE,
    WINDOWS_NATIVE_EXECUTOR,
    WINDOWS_REAL_BOOT,
    WINDOWS_REAL_BOOT_QEMU,
)


@dataclass(frozen=True)
class Route:
    capability: str
    executor: str
    mode: str
    single_flight: bool = True


WINDOWS_QEMU_ROUTE = Route(
    capability=WINDOWS_REAL_BOOT,
    executor="windows-real-boot-qemu",
    mode=WINDOWS_REAL_BOOT_QEMU,
)
WINDOWS_NATIVE_ROUTE = Route(
    capability=WINDOWS_NATIVE_EXECUTOR,
    executor=WINDOWS_NATIVE_EXECUTOR,
    mode=WINDOWS_NATIVE_EXECUTOR,
)
WINDOWS_CLOUD_ROUTE = Route(
    capability=WINDOWS_CLOUD_NATIVE,
    executor="windows-server-2025-cloud",
    mode=WINDOWS_CLOUD_NATIVE,
)


def route_windows(
    capability: str,
    metadata: Mapping[str, Any] | None = None,
) -> Route:
    """Return the only valid route for a Windows capability.

    QEMU real-boot and provider-native Windows are intentionally distinct.
    Metadata is used only to prevent accidental mode substitution.
    """
    data = dict(metadata or {})

    if capability == WINDOWS_REAL_BOOT:
        executor = str(data.get("executor", "")).strip().lower()
        if executor != WINDOWS_QEMU_ROUTE.executor:
            raise RuntimeError("WINDOWS_REAL_BOOT_REQUIRES_QEMU_CLOUD")
        return WINDOWS_QEMU_ROUTE

    if capability == WINDOWS_NATIVE_EXECUTOR:
        return WINDOWS_NATIVE_ROUTE

    if capability == WINDOWS_CLOUD_NATIVE:
        return WINDOWS_CLOUD_ROUTE

    raise RuntimeError(f"NO_WINDOWS_ROUTE_FOR:{capability}")


def assert_single_flight(route: Route, active_runs: int) -> None:
    """Reject concurrent consequential execution for a routed capability."""
    if not route.single_flight:
        return
    if active_runs < 0:
        raise ValueError("ACTIVE_RUNS_INVALID")
    if active_runs > 0:
        raise RuntimeError(
            f"EXECUTOR_SINGLE_FLIGHT_BUSY:{route.executor}"
        )
