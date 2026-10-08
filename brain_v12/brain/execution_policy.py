from __future__ import annotations

"""Brain execution policy.

GitHub is an evidence/source-of-truth channel, not the Brain's execution
dependency. Internal execution is preferred and external CI is never an
implicit fallback for real runtime capabilities.
"""

from dataclasses import dataclass
from typing import Iterable

WINDOWS_REAL_BOOT = "windows-server-2025-real-boot"
BRAIN_INTERNAL = "brain-internal"
GITHUB_CI = "github-ci"
WINDOWS_CLOUD = "windows-server-2025-cloud"
WINDOWS_CLOUD_NATIVE = "windows-server-2025-cloud-native"
WINDOWS_REAL_BOOT_QEMU = "windows-server-2025-real-boot-qemu"


@dataclass(frozen=True)
class Executor:
    name: str
    capabilities: frozenset[str]
    priority: int = 100
    external: bool = False


def default_executors() -> tuple[Executor, ...]:
    return (
        Executor(
            name=BRAIN_INTERNAL,
            capabilities=frozenset({"brain-internal-execution", "qemu"}),
            priority=0,
            external=False,
        ),
        Executor(
            name=WINDOWS_CLOUD,
            capabilities=frozenset({WINDOWS_CLOUD, WINDOWS_CLOUD_NATIVE}),
            priority=50,
            external=True,
        ),
        Executor(
            name=GITHUB_CI,
            capabilities=frozenset({"ci-verification"}),
            priority=1000,
            external=True,
        ),
    )


def choose_executor(executors: Iterable[Executor], capability: str) -> Executor:
    candidates = [e for e in executors if capability in e.capabilities]
    if not candidates:
        raise RuntimeError(f"NO_EXECUTOR_FOR:{capability}")

    selected = sorted(candidates, key=lambda e: (e.priority, e.name))[0]

    # Real runtime capabilities may use an explicitly configured cloud provider,
    # but must never silently fall back to GitHub CI.

    if capability == WINDOWS_REAL_BOOT and selected.external:
        raise RuntimeError("EXTERNAL_EXECUTOR_FORBIDDEN")

    return selected
