"""Estimated power, thermal, cooling and fault models for virtual hardware.

All watts and temperatures are ESTIMATES unless a profile explicitly carries
physical calibration evidence. These models are for capacity planning and
fault testing, not electrical/thermal safety certification.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import hashlib
import json
import math
from typing import Any, Iterable


MODEL_VERSION = "1.0"
ESTIMATE_LABEL = "ESTIMATE_NOT_PHYSICALLY_CALIBRATED"


@dataclass(frozen=True)
class PowerThermalProfile:
    """Per-device parameters; defaults are illustrative estimates, not specs."""
    device_id: str
    device_type: str
    idle_watts: float = 8.0
    max_watts: float = 65.0
    ambient_c: float = 25.0
    thermal_resistance_c_per_w: float = 0.35
    thermal_capacitance_j_per_c: float = 180.0
    cooling_effectiveness: float = 1.0
    temperature_limit_c: float = 85.0
    throttle_start_c: float = 75.0
    fan_min_rpm: int = 700
    fan_max_rpm: int = 5000
    fan_curve_start_c: float = 35.0
    fan_curve_full_c: float = 80.0
    calibration: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if not self.device_id or not self.device_type:
            raise ValueError("POWER_PROFILE_DEVICE_REQUIRED")
        if self.idle_watts < 0 or self.max_watts < self.idle_watts:
            raise ValueError("POWER_PROFILE_INVALID_WATTS")
        if self.thermal_resistance_c_per_w <= 0 or self.thermal_capacitance_j_per_c <= 0:
            raise ValueError("POWER_PROFILE_INVALID_THERMAL_CONSTANT")
        if not 0 < self.cooling_effectiveness <= 1:
            raise ValueError("POWER_PROFILE_INVALID_COOLING")
        if self.ambient_c >= self.throttle_start_c or self.throttle_start_c >= self.temperature_limit_c:
            raise ValueError("POWER_PROFILE_INVALID_TEMPERATURE_LIMITS")
        if self.fan_min_rpm < 0 or self.fan_max_rpm < self.fan_min_rpm:
            raise ValueError("POWER_PROFILE_INVALID_FAN_CURVE")

    @property
    def calibrated(self) -> bool:
        c = self.calibration or {}
        return bool(c.get("verified") is True and c.get("measurement_source") and c.get("measured_at"))

    def evidence_label(self) -> str:
        return "CALIBRATED_TO_PHYSICAL_MEASUREMENTS" if self.calibrated else ESTIMATE_LABEL


@dataclass
class DeviceTelemetry:
    device_id: str
    temperature_c: float
    power_watts: float
    fan_rpm: int
    throttle_factor: float
    throttled: bool
    over_temperature: bool
    estimate_label: str
    workload: float
    timestamp_s: float


@dataclass
class PowerThermalModel:
    """First-order thermal RC model advanced only by explicit elapsed seconds."""
    profile: PowerThermalProfile
    temperature_c: float | None = None
    workload: float = 0.0
    elapsed_s: float = 0.0
    last_power_watts: float = 0.0
    events: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.temperature_c is None:
            self.temperature_c = self.profile.ambient_c
        self.temperature_c = float(self.temperature_c)
        if not math.isfinite(self.temperature_c):
            raise ValueError("THERMAL_INVALID_INITIAL_TEMPERATURE")

    def set_workload(self, utilization: float) -> None:
        if not math.isfinite(utilization) or not 0 <= utilization <= 1:
            raise ValueError("WORKLOAD_MUST_BE_0_TO_1")
        old = self.workload
        self.workload = utilization
        if old != utilization:
            self.events.append({"type": "WORKLOAD_CHANGED", "from": old, "to": utilization, "time_s": self.elapsed_s})

    def estimated_power_watts(self, workload: float | None = None) -> float:
        u = self.workload if workload is None else workload
        if not 0 <= u <= 1:
            raise ValueError("WORKLOAD_MUST_BE_0_TO_1")
        return self.profile.idle_watts + (self.profile.max_watts - self.profile.idle_watts) * u

    def _throttle_factor(self) -> float:
        p = self.profile
        if self.temperature_c <= p.throttle_start_c:
            return 1.0
        if self.temperature_c >= p.temperature_limit_c:
            return 0.0
        return (p.temperature_limit_c - self.temperature_c) / (p.temperature_limit_c - p.throttle_start_c)

    def _fan_rpm(self) -> int:
        p = self.profile
        fraction = min(1.0, max(0.0, (self.temperature_c - p.fan_curve_start_c) /
                                     (p.fan_curve_full_c - p.fan_curve_start_c)))
        return round(p.fan_min_rpm + fraction * (p.fan_max_rpm - p.fan_min_rpm))

    def advance(self, dt_s: float) -> DeviceTelemetry:
        if not math.isfinite(dt_s) or dt_s <= 0:
            raise ValueError("THERMAL_STEP_MUST_BE_POSITIVE")
        p = self.profile
        pre_factor = self._throttle_factor()
        raw_power = self.estimated_power_watts()
        power = p.idle_watts + (raw_power - p.idle_watts) * pre_factor
        # Equivalent cooling conductance is adjusted by the configured fan effectiveness.
        r_eff = p.thermal_resistance_c_per_w / p.cooling_effectiveness
        tau = r_eff * p.thermal_capacitance_j_per_c
        steady = p.ambient_c + power * r_eff
        old_temp = self.temperature_c
        self.temperature_c = steady + (old_temp - steady) * math.exp(-dt_s / tau)
        self.elapsed_s += dt_s
        self.last_power_watts = power
        factor = self._throttle_factor()
        throttled = factor < 0.999999
        over_temp = self.temperature_c >= p.temperature_limit_c
        if throttled and not (self.events and self.events[-1].get("type") == "THERMAL_THROTTLE"):
            self.events.append({"type": "THERMAL_THROTTLE", "temperature_c": self.temperature_c, "time_s": self.elapsed_s})
        if not throttled and self.events and self.events[-1].get("type") == "THERMAL_THROTTLE":
            self.events.append({"type": "THERMAL_RECOVERED", "temperature_c": self.temperature_c, "time_s": self.elapsed_s})
        return DeviceTelemetry(p.device_id, self.temperature_c, power, self._fan_rpm(), factor,
                               throttled, over_temp, p.evidence_label(), self.workload, self.elapsed_s)

    def snapshot(self) -> dict[str, Any]:
        return {"model_version": MODEL_VERSION, "profile": asdict(self.profile),
                "temperature_c": self.temperature_c, "workload": self.workload,
                "elapsed_s": self.elapsed_s, "last_power_watts": self.last_power_watts,
                "estimate_label": self.profile.evidence_label(), "events": list(self.events)}


class FaultType(str, Enum):
    MEMORY_ERROR = "memory_error"
    STORAGE_TIMEOUT = "storage_timeout"
    NETWORK_LOSS = "network_loss"
    DEVICE_RESET = "device_reset"
    POWER_INTERRUPTION = "power_interruption"


@dataclass
class FaultController:
    """Deterministic, opt-in fault injection with explicit recovery/evidence."""
    enabled: bool = False
    events: list[dict[str, Any]] = field(default_factory=list)
    active_faults: dict[str, dict[str, Any]] = field(default_factory=dict)
    preserved_queue_ids: list[str] = field(default_factory=list)

    def inject(self, fault: FaultType | str, *, target: str, event_id: str,
               queued_task_ids: Iterable[str] = (), details: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("FAULT_INJECTION_DISABLED")
        kind = FaultType(fault)
        if not target or not event_id:
            raise ValueError("FAULT_TARGET_AND_EVENT_ID_REQUIRED")
        if event_id in self.active_faults or any(e["event_id"] == event_id for e in self.events):
            raise ValueError("FAULT_EVENT_ID_DUPLICATE")
        queue_ids = list(queued_task_ids)
        if len(queue_ids) != len(set(queue_ids)):
            raise ValueError("FAULT_QUEUE_IDS_NOT_UNIQUE")
        self.preserved_queue_ids = list(dict.fromkeys(self.preserved_queue_ids + queue_ids))
        record = {"event_id": event_id, "fault": kind.value, "target": target,
                  "details": dict(details or {}), "queue_preservation": "PRESERVED_BY_MODEL",
                  "recovered": False, "sequence": len(self.events) + 1}
        self.active_faults[event_id] = record
        self.events.append(record)
        return dict(record)

    def recover(self, event_id: str, *, recovery_evidence: dict[str, Any] | None = None) -> dict[str, Any]:
        if event_id not in self.active_faults:
            raise KeyError("FAULT_NOT_ACTIVE")
        record = self.active_faults.pop(event_id)
        record["recovered"] = True
        record["recovery_evidence"] = dict(recovery_evidence or {})
        record["recovery_status"] = "EVIDENCE_RECORDED" if recovery_evidence else "RECOVERED_WITHOUT_EXTERNAL_EVIDENCE"
        return dict(record)

    def report(self) -> dict[str, Any]:
        stable = {"events": self.events, "active_fault_ids": sorted(self.active_faults),
                  "preserved_queue_ids": self.preserved_queue_ids}
        digest = hashlib.sha256(json.dumps(stable, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return {"ok": not self.active_faults, "model_version": MODEL_VERSION,
                "injection_enabled": self.enabled, "events": list(self.events),
                "active_fault_ids": sorted(self.active_faults),
                "preserved_queue_ids": list(self.preserved_queue_ids),
                "evidence_sha256": digest, "physical_validation": False,
                "notice": "Fault effects are simulated; queue preservation is a model assertion, not proof of external queue durability."}


def default_profile(device_id: str, device_type: str) -> PowerThermalProfile:
    """Return transparent generic estimates; do not represent these as vendor specs."""
    defaults = {
        "cpu": (12.0, 95.0, 0.30, 220.0, 0.9, 95.0, 82.0),
        "gpu": (18.0, 250.0, 0.22, 500.0, 0.95, 88.0, 78.0),
        "memory": (2.0, 12.0, 0.55, 90.0, 0.85, 85.0, 75.0),
        "storage": (1.0, 10.0, 0.8, 45.0, 0.8, 70.0, 60.0),
        "network": (2.0, 18.0, 0.65, 60.0, 0.8, 80.0, 70.0),
        "system": (15.0, 180.0, 0.25, 400.0, 0.9, 90.0, 80.0),
    }
    idle, peak, resistance, capacitance, cooling, limit, throttle = defaults.get(
        device_type.lower(), (5.0, 40.0, 0.5, 120.0, 0.85, 85.0, 75.0))
    return PowerThermalProfile(device_id=device_id, device_type=device_type,
        idle_watts=idle, max_watts=peak, thermal_resistance_c_per_w=resistance,
        thermal_capacitance_j_per_c=capacitance, cooling_effectiveness=cooling,
        temperature_limit_c=limit, throttle_start_c=throttle)
