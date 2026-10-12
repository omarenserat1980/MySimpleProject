"""Software-only baseline models for Bitcoin ASIC mining hardware.

This module estimates device behavior for simulation and testing. It does not
mine real Bitcoin, control physical miners, connect to pools, or guarantee
vendor-level accuracy. Power/hash figures are configurable estimates unless
calibrated against measured hardware.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class MinerState(str, Enum):
    OFF = "off"
    BOOTING = "booting"
    MINING_SIMULATED = "mining_simulated"
    THROTTLED = "throttled"
    FAULT = "fault"


@dataclass(frozen=True)
class ASICProfile:
    profile_id: str
    label: str
    hash_rate_th_s: float
    nominal_power_w: float
    hashboards: int = 3
    chips_per_hashboard: int = 100
    inlet_limit_c: float = 35.0
    shutdown_c: float = 95.0
    fan_count: int = 4
    source_kind: str = "configurable_baseline_estimate"

    def validate(self) -> None:
        if not self.profile_id or not self.label:
            raise ValueError("profile_id and label are required")
        if self.hash_rate_th_s <= 0 or self.nominal_power_w <= 0:
            raise ValueError("hash rate and power must be positive")
        if min(self.hashboards, self.chips_per_hashboard, self.fan_count) < 1:
            raise ValueError("hardware counts must be positive")
        if self.shutdown_c <= self.inlet_limit_c:
            raise ValueError("shutdown_c must exceed inlet_limit_c")


# Generic starter profiles, not claims about any exact commercial SKU.
DEFAULT_ASIC_PROFILES: dict[str, ASICProfile] = {
    "asic_entry": ASICProfile("asic_entry", "Entry ASIC (baseline)", 30.0, 3000.0, 3, 80, source_kind="illustrative_estimate"),
    "asic_midrange": ASICProfile("asic_midrange", "Midrange ASIC (baseline)", 100.0, 3500.0, 3, 100, source_kind="illustrative_estimate"),
    "asic_high_density": ASICProfile("asic_high_density", "High-density ASIC (baseline)", 200.0, 5500.0, 4, 120, source_kind="illustrative_estimate"),
}


@dataclass
class MiningFaults:
    hashboard_failed: set[int] = field(default_factory=set)
    fan_failed: set[int] = field(default_factory=set)
    psu_available: bool = True
    network_available: bool = True
    controller_available: bool = True
    injected_power_loss: bool = False


@dataclass
class MiningHardwareState:
    state: MinerState = MinerState.OFF
    inlet_temperature_c: float = 25.0
    estimated_chip_temperature_c: float = 35.0
    fan_pwm_percent: float = 35.0
    estimated_power_w: float = 0.0
    effective_hash_rate_th_s: float = 0.0
    accepted_work_units: int = 0
    rejected_work_units: int = 0
    last_faults: list[str] = field(default_factory=list)


class VirtualASICMiner:
    """Deterministic, transaction-level ASIC miner model; never performs real mining."""

    def __init__(
        self,
        profile: ASICProfile | None = None,
        *,
        ambient_temperature_c: float = 25.0,
        cooling_effectiveness: float = 0.75,
        faults: MiningFaults | None = None,
    ) -> None:
        self.profile = profile or DEFAULT_ASIC_PROFILES["asic_midrange"]
        self.profile.validate()
        if not 0.0 <= cooling_effectiveness <= 1.0:
            raise ValueError("cooling_effectiveness must be between 0 and 1")
        self.cooling_effectiveness = cooling_effectiveness
        self.faults = faults or MiningFaults()
        self.data = MiningHardwareState(inlet_temperature_c=float(ambient_temperature_c),
                                        estimated_chip_temperature_c=float(ambient_temperature_c))
        self._thermal_momentum = 0.0

    def start(self) -> dict[str, Any]:
        self.data.last_faults = []
        if self.faults.injected_power_loss or not self.faults.psu_available:
            self.data.state = MinerState.FAULT
            self.data.last_faults.append("power_unavailable")
        elif not self.faults.controller_available:
            self.data.state = MinerState.FAULT
            self.data.last_faults.append("controller_unavailable")
        elif not self.faults.network_available:
            self.data.state = MinerState.FAULT
            self.data.last_faults.append("network_unavailable")
        else:
            self.data.state = MinerState.MINING_SIMULATED
        return self.snapshot()

    def stop(self) -> dict[str, Any]:
        self.data.state = MinerState.OFF
        self.data.estimated_power_w = 0.0
        self.data.effective_hash_rate_th_s = 0.0
        return self.snapshot()

    def inject_fault(self, fault: str, index: int | None = None, enabled: bool = True) -> None:
        if fault == "hashboard":
            if index is None or not 0 <= index < self.profile.hashboards:
                raise ValueError("valid hashboard index required")
            (self.faults.hashboard_failed.add if enabled else self.faults.hashboard_failed.discard)(index)
        elif fault == "fan":
            if index is None or not 0 <= index < self.profile.fan_count:
                raise ValueError("valid fan index required")
            (self.faults.fan_failed.add if enabled else self.faults.fan_failed.discard)(index)
        elif fault in {"psu", "network", "controller", "power_loss"}:
            attr = {"psu": "psu_available", "network": "network_available",
                    "controller": "controller_available", "power_loss": "injected_power_loss"}[fault]
            setattr(self.faults, attr, (not enabled) if fault != "power_loss" else enabled)
        else:
            raise ValueError(f"unsupported fault: {fault}")

    def tick(self, seconds: float = 1.0, *, inlet_temperature_c: float | None = None) -> dict[str, Any]:
        if seconds <= 0:
            raise ValueError("seconds must be positive")
        if inlet_temperature_c is not None:
            self.data.inlet_temperature_c = float(inlet_temperature_c)
        self.data.last_faults = []
        active = self.data.state in {MinerState.MINING_SIMULATED, MinerState.THROTTLED}
        if self.faults.injected_power_loss or not self.faults.psu_available:
            self.data.last_faults.append("power_unavailable")
            self.data.state = MinerState.FAULT
            active = False
        if not self.faults.controller_available:
            self.data.last_faults.append("controller_unavailable")
            self.data.state = MinerState.FAULT
            active = False
        if not self.faults.network_available:
            self.data.last_faults.append("network_unavailable")
            self.data.state = MinerState.FAULT
            active = False
        if len(self.faults.hashboard_failed) >= self.profile.hashboards:
            self.data.last_faults.append("all_hashboards_failed")
            self.data.state = MinerState.FAULT
            active = False

        board_factor = (self.profile.hashboards - len(self.faults.hashboard_failed)) / self.profile.hashboards
        fan_factor = max(0.0, 1.0 - len(self.faults.fan_failed) / self.profile.fan_count)
        cooling = self.cooling_effectiveness * fan_factor
        load = 1.0 if active else 0.0
        target_temp = self.data.inlet_temperature_c + (self.profile.nominal_power_w / 1000.0) * (0.7 + 1.2 * load) * (1.0 - cooling)
        # Stable first-order thermal approximation; values are estimates, not calibrated measurements.
        alpha = min(1.0, seconds / 45.0)
        self.data.estimated_chip_temperature_c += (target_temp - self.data.estimated_chip_temperature_c) * alpha
        self._thermal_momentum = max(0.0, self._thermal_momentum + (load * (1.0 - cooling) * seconds / 120.0))
        too_hot = self.data.estimated_chip_temperature_c >= self.profile.shutdown_c
        fan_fail_overheat = bool(self.faults.fan_failed) and self.data.estimated_chip_temperature_c >= self.profile.inlet_limit_c + 30
        if too_hot or fan_fail_overheat:
            self.data.state = MinerState.THROTTLED if active else self.data.state
            self.data.last_faults.append("thermal_limit_or_cooling_degraded")
            load *= 0.5
        if active and self.data.state != MinerState.FAULT:
            self.data.effective_hash_rate_th_s = self.profile.hash_rate_th_s * board_factor * load
            self.data.estimated_power_w = self.profile.nominal_power_w * (0.12 + 0.88 * load)
            self.data.fan_pwm_percent = min(100.0, max(25.0, 35.0 + max(0.0, self.data.estimated_chip_temperature_c - 40.0) * 1.5))
        else:
            self.data.effective_hash_rate_th_s = 0.0
            self.data.estimated_power_w = 8.0 if self.data.state != MinerState.OFF and self.faults.psu_available else 0.0
            self.data.fan_pwm_percent = 0.0 if self.data.state == MinerState.OFF else 25.0
        return self.snapshot()

    def submit_simulated_work(self, units: int = 1, *, accepted: bool = True) -> dict[str, Any]:
        if units < 0:
            raise ValueError("units must not be negative")
        if self.data.state not in {MinerState.MINING_SIMULATED, MinerState.THROTTLED}:
            raise RuntimeError("miner is not in simulated mining state")
        if accepted:
            self.data.accepted_work_units += units
        else:
            self.data.rejected_work_units += units
        return self.snapshot()

    def snapshot(self) -> dict[str, Any]:
        return {
            "profile": asdict(self.profile),
            "state": self.data.state.value,
            "hardware": {
                "asic_chips": self.profile.hashboards * self.profile.chips_per_hashboard,
                "hashboards": self.profile.hashboards,
                "fans": self.profile.fan_count,
                "psu_available": self.faults.psu_available,
                "controller_available": self.faults.controller_available,
                "network_available": self.faults.network_available,
            },
            "estimated": {
                "hash_rate_th_s": round(self.data.effective_hash_rate_th_s, 6),
                "power_w": round(self.data.estimated_power_w, 3),
                "chip_temperature_c": round(self.data.estimated_chip_temperature_c, 3),
                "fan_pwm_percent": round(self.data.fan_pwm_percent, 2),
                "joules_per_th_estimate": round(self.data.estimated_power_w / self.data.effective_hash_rate_th_s, 6)
                    if self.data.effective_hash_rate_th_s > 0 else None,
                "is_calibrated": False,
            },
            "work_simulation": {
                "accepted_units": self.data.accepted_work_units,
                "rejected_units": self.data.rejected_work_units,
                "real_bitcoin_mining": False,
                "pool_connection": False,
            },
            "faults": list(self.data.last_faults),
            "fidelity": "functional_estimate_not_cycle_accurate",
        }
