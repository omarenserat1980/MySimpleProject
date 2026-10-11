"""Simulation-first Arkan gateway with explicitly verified real-device promotion."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from .arkan_device_emulator import ArkanDeviceEmulator, ArkanProfile
from .digital_twin_fabric import Reality, RealityGate
from .real_arkan_probe import RealArkanProbeValidator

SCHEMA = "brain.arkan-failover-gateway.v1"

@dataclass(frozen=True)
class ArkanEndpoint:
    node_id: str
    mode: str
    reality: str
    reason: str

class ArkanFailoverGateway:
    """One logical Arkan endpoint; simulation is default, real promotion is explicit."""
    def __init__(
        self,
        virtual_root: str | Path,
        *,
        real_probe: Callable[[], dict[str, Any]] | None = None,
        profile: ArkanProfile | None = None,
        prefer_real: bool = False,
    ):
        self.profile = profile or ArkanProfile()
        self.real_probe = real_probe
        self.prefer_real = bool(prefer_real)
        self.validator = RealArkanProbeValidator()
        self.virtual = ArkanDeviceEmulator(virtual_root, self.profile)
        self.mode = "UNAVAILABLE"
        self.last_real_evidence: dict[str, Any] | None = None
        self.last_reason = "NOT_CONNECTED"

    def connect(self) -> dict[str, Any]:
        """Connect to the virtual twin first unless real-first is explicitly configured."""
        if not self.prefer_real:
            return self._activate_virtual("SIMULATION_FIRST_POLICY")
        if self._try_real():
            return self.status()
        return self._activate_virtual(self.last_reason)

    def _try_real(self) -> bool:
        if self.real_probe is None:
            self.last_reason = "REAL_PROBE_NOT_CONFIGURED"
            return False
        try:
            evidence = self.real_probe()
            self.validator.validate(evidence)
            gate = RealityGate.accept(evidence, Reality.REAL)
            if not gate.get("ok"):
                self.last_reason = str(gate.get("status", "REALITY_GATE_REJECTED"))
                return False
            self.mode = "REAL"
            self.last_real_evidence = dict(evidence)
            self.last_reason = "REAL_HEARTBEAT_VERIFIED"
            return True
        except Exception as exc:
            self.last_reason = f"REAL_UNAVAILABLE:{type(exc).__name__}"
            return False

    def failover(self, reason: str = "REAL_ENDPOINT_UNAVAILABLE") -> dict[str, Any]:
        return self._activate_virtual(reason)

    def recover_real(self) -> dict[str, Any]:
        """Explicitly attempt promotion to REAL; invalid/stale evidence stays virtual."""
        if self._try_real():
            return self.status()
        return self._activate_virtual(self.last_reason)

    def _activate_virtual(self, reason: str) -> dict[str, Any]:
        self.mode = "VIRTUAL"
        self.last_reason = reason
        return self.status()

    def status(self) -> dict[str, Any]:
        reality = Reality.REAL.value if self.mode == "REAL" else Reality.SIMULATED.value if self.mode == "VIRTUAL" else "UNKNOWN"
        return {
            "ok": self.mode in {"REAL", "VIRTUAL"},
            "schema": SCHEMA,
            "logical_node_id": self.profile.device_id,
            "logical_name": self.profile.name,
            "mode": self.mode,
            "reality": reality,
            "policy": "REAL_FIRST" if self.prefer_real else "SIMULATION_FIRST",
            "reason": self.last_reason,
            "real_evidence_present": self.last_real_evidence is not None,
            "virtual_ready": True,
        }

    def endpoint(self) -> dict[str, Any]:
        if self.mode == "VIRTUAL":
            return {
                "ok": True, "mode": "VIRTUAL", "reality": Reality.SIMULATED.value,
                "desktop_commander": self.virtual.desktop,
                "powershell": self.virtual.powershell,
                "device": self.virtual,
            }
        if self.mode == "REAL":
            return {
                "ok": True, "mode": "REAL", "reality": Reality.REAL.value,
                "device_id": self.profile.device_id, "evidence": self.last_real_evidence,
            }
        return {"ok": False, "status": "ARKAN_ENDPOINT_UNAVAILABLE"}

    def run_powershell(self, script: str) -> dict[str, Any]:
        if self.mode != "VIRTUAL":
            return {
                "ok": False,
                "status": "REAL_ENDPOINT_COMMAND_REQUIRES_REMOTE_AGENT",
                "reality": Reality.REAL.value,
            }
        return self.virtual.powershell.run(script)

    def heartbeat(self) -> dict[str, Any]:
        if self.mode == "VIRTUAL":
            hb = self.virtual.heartbeat()
            hb.update({"mode": "VIRTUAL", "reality": Reality.SIMULATED.value})
            return hb
        if self.mode == "REAL" and self.last_real_evidence:
            return {
                "ok": True, "node_id": self.profile.device_id, "name": self.profile.name,
                "state": "ONLINE", "mode": "REAL", "reality": Reality.REAL.value,
                "heartbeat": "FRESH",
                "heartbeat_at": self.last_real_evidence.get("heartbeat_at"),
            }
        return {"ok": False, "status": "ARKAN_ENDPOINT_UNAVAILABLE"}

__all__ = ["ArkanEndpoint", "ArkanFailoverGateway", "SCHEMA"]
