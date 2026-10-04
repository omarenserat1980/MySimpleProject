from __future__ import annotations

"""Brain execution policy.

GitHub is one executor/verification channel, not the Brain's only runtime.
"""

from dataclasses import dataclass
from typing import Iterable

WINDOWS_REAL_BOOT = "windows-server-2025-real-boot"


@dataclass(frozen=True)
class Executor:
    name: str
    capabilities: frozenset[str]
    priority: int = 100


def choose_executor(executors: Iterable[Executor], capability: str) -> Executor:
    candidates = [e for e in executors if capability in e.capabilities]
    if not candidates:
        raise RuntimeError(f"NO_EXECUTOR_FOR:{capability}")
    return sorted(candidates, key=lambda e: (e.priority, e.name))[0]
