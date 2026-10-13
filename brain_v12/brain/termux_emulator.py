"""Sandboxed Termux simulator; never executes host shell commands."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class TermuxSimulationResult:
    ok: bool
    mode: str
    command: tuple[str, ...]
    simulated_output: str
    executed: bool = False
    reality_level: str = "SIMULATED"

    def public(self) -> dict[str, Any]:
        return asdict(self)


class TermuxEmulator:
    """Deterministic command-shape simulator for tests, not a Termux shell."""

    def describe(self) -> dict[str, Any]:
        return {
            "simulator_id": "termux-brain",
            "platform": "android-termux-simulator",
            "status": "SIMULATOR_READY",
            "reality_level": "SIMULATED",
            "host_commands_executed": False,
        }

    def simulate(self, argv: list[str] | tuple[str, ...]) -> dict[str, Any]:
        command = tuple(str(part) for part in argv)
        if not command or any("\x00" in part for part in command):
            return TermuxSimulationResult(
                False, "SIMULATED", command, "INVALID_SIMULATED_COMMAND"
            ).public()
        return TermuxSimulationResult(
            True, "SIMULATED", command,
            "SIMULATED_ONLY: no Android shell or host process was executed",
        ).public()
