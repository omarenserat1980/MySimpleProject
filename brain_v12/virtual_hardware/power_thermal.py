"""Deterministic, explicitly estimated power/thermal model for virtual machines."""
from __future__ import annotations

from dataclasses import dataclass, field
import math


@dataclass
class PowerThermalModel:
    """Lumped thermal RC approximation; never a physical sensor or calibrated power meter."""
    ambient_c: float = 25.0
    thermal_capacity_j_per_c: float = 60.0
    cooling_w_per_c: float = 2.5
    throttle_c: float = 85.0
    shutdown_c: float = 100.0
    idle_power_watts: float = 20.0
    peak_power_watts: float = 150.0
    temperature_c: float = 25.0
    cooling_enabled: bool = True
    sensor_enabled: bool = True
    throttled: bool = False
    shutdown_required: bool = False
    simulated_seconds: float = 0.0
    _next_fault: str | None = None
    history: list[dict] = field(default_factory=list)

    def __post_init__(self):
        if self.thermal_capacity_j_per_c <= 0 or self.cooling_w_per_c < 0:
            raise ValueError("THERMAL_PARAMETERS_INVALID")
        if not self.ambient_c < self.throttle_c < self.shutdown_c:
            raise ValueError("THERMAL_LIMITS_INVALID")
        if self.idle_power_watts < 0 or self.peak_power_watts < self.idle_power_watts:
            raise ValueError("POWER_BUDGET_INVALID")

    def inject_fault(self, fault: str) -> dict:
        if fault not in {"cooling_failure", "sensor_failure", "temperature_spike", "power_interruption"}:
            raise ValueError(f"POWER_THERMAL_UNKNOWN_FAULT:{fault}")
        self._next_fault = fault
        return {"ok": True, "fault": fault, "deterministic": True}

    def fan_speed_percent(self, temperature_c: float | None = None) -> int:
        temp = self.temperature_c if temperature_c is None else temperature_c
        points = ((30.0, 0.0), (45.0, 25.0), (60.0, 55.0), (75.0, 85.0), (85.0, 100.0))
        if temp <= points[0][0]:
            return 0
        for (t0, f0), (t1, f1) in zip(points, points[1:]):
            if temp <= t1:
                return int(round(f0 + (f1 - f0) * (temp - t0) / (t1 - t0)))
        return 100

    def update(self, load_fraction: float, dt_seconds: float, power_watts: float | None = None) -> dict:
        if not 0.0 <= load_fraction <= 1.0:
            raise ValueError("THERMAL_LOAD_FRACTION_OUT_OF_RANGE")
        if dt_seconds <= 0:
            raise ValueError("THERMAL_TIMESTEP_MUST_BE_POSITIVE")
        fault = self._next_fault
        self._next_fault = None
        if fault == "cooling_failure":
            self.cooling_enabled = False
        elif fault == "sensor_failure":
            self.sensor_enabled = False
        elif fault == "temperature_spike":
            self.temperature_c = max(self.temperature_c, self.throttle_c + 5.0)
        elif fault == "power_interruption":
            self.temperature_c = max(self.ambient_c, self.temperature_c - 1.0)
            self.simulated_seconds += dt_seconds
            result = self.status()
            result.update({"power_interrupted": True, "estimated_power_watts": 0.0})
            self.history.append(dict(result))
            return result

        requested = (power_watts if power_watts is not None else
                     self.idle_power_watts + (self.peak_power_watts - self.idle_power_watts) * load_fraction)
        if requested < 0:
            raise ValueError("THERMAL_POWER_WATTS_NEGATIVE")
        if self.temperature_c >= self.throttle_c:
            self.throttled = True
        elif self.temperature_c < self.throttle_c - 5:
            self.throttled = False
        effective = self.idle_power_watts + max(0.0, requested - self.idle_power_watts) * (0.6 if self.throttled else 1.0)
        cooling = self.cooling_w_per_c if self.cooling_enabled else 0.0
        if cooling > 0:
            equilibrium = self.ambient_c + effective / cooling
            self.temperature_c = equilibrium + (self.temperature_c - equilibrium) * math.exp(
                -cooling * dt_seconds / self.thermal_capacity_j_per_c)
        else:
            self.temperature_c += effective * dt_seconds / self.thermal_capacity_j_per_c
        self.simulated_seconds += dt_seconds
        if self.temperature_c >= self.shutdown_c:
            self.shutdown_required = True
        if self.temperature_c < self.throttle_c - 5:
            self.throttled = False
        elif self.temperature_c >= self.throttle_c:
            self.throttled = True
        result = self.status()
        result.update({"requested_power_watts": requested, "estimated_power_watts": effective,
                       "load_fraction": load_fraction, "dt_seconds": dt_seconds,
                       "power_interrupted": False})
        self.history.append(dict(result))
        return result

    def status(self) -> dict:
        return {
            "temperature_c_estimate": self.temperature_c,
            "ambient_c_assumption": self.ambient_c,
            "cooling_enabled": self.cooling_enabled,
            "cooling_w_per_c_assumption": self.cooling_w_per_c,
            "fan_speed_percent_estimate": self.fan_speed_percent(),
            "throttled_estimate": self.throttled,
            "shutdown_required_estimate": self.shutdown_required,
            "sensor_status": "estimated" if self.sensor_enabled else "faulted",
            "thermal_capacity_j_per_c_assumption": self.thermal_capacity_j_per_c,
            "simulated_seconds": self.simulated_seconds,
            "temperature_is_physical_measurement": False,
            "power_is_physical_measurement": False,
            "calibrated_against_hardware": False,
            "model_fidelity": "lumped_thermal_rc_estimate",
        }

    def snapshot(self) -> dict:
        return {"ambient_c": self.ambient_c, "thermal_capacity_j_per_c": self.thermal_capacity_j_per_c,
                "cooling_w_per_c": self.cooling_w_per_c, "throttle_c": self.throttle_c,
                "shutdown_c": self.shutdown_c, "idle_power_watts": self.idle_power_watts,
                "peak_power_watts": self.peak_power_watts, "temperature_c": self.temperature_c,
                "cooling_enabled": self.cooling_enabled, "sensor_enabled": self.sensor_enabled,
                "throttled": self.throttled, "shutdown_required": self.shutdown_required,
                "simulated_seconds": self.simulated_seconds}

    def restore(self, snapshot: dict) -> dict:
        for name in ("ambient_c", "thermal_capacity_j_per_c", "cooling_w_per_c", "throttle_c",
                     "shutdown_c", "idle_power_watts", "peak_power_watts", "temperature_c",
                     "cooling_enabled", "sensor_enabled", "throttled", "shutdown_required", "simulated_seconds"):
            if name in snapshot:
                setattr(self, name, snapshot[name])
        self.__post_init__()
        self._next_fault = None
        self.history = []
        return {"ok": True, **self.status()}
