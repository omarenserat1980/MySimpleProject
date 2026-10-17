"""Digital power/thermal model for BRAIN-ASIC-001.

This is an illustrative software model, NOT a measurement, electrical simulation,
or calibrated model of a real ASIC. Replace defaults only with datasheet values
and measured calibration data. All output values are tagged SIMULATED.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math
from typing import Any


@dataclass(frozen=True)
class ModelParams:
    # Illustrative example parameters only; not specifications for any real chip.
    input_voltage_v: float = 12.0
    idle_power_w: float = 3.0
    max_power_w: float = 60.0
    conversion_efficiency: float = 0.90
    ambient_temp_c: float = 25.0
    thermal_resistance_c_per_w: float = 0.55
    thermal_capacitance_j_per_c: float = 120.0
    fan_cooling_factor: float = 1.0


class ModelInputError(ValueError):
    pass


def simulate_step(
    utilization: float,
    duration_s: float,
    previous_temp_c: float | None = None,
    params: ModelParams = ModelParams(),
) -> dict[str, Any]:
    """Advance one first-order thermal RC step at a constant workload.

    Utilization must be 0..1. Values are illustrative until calibrated.
    """
    if not math.isfinite(utilization) or not 0.0 <= utilization <= 1.0:
        raise ModelInputError("utilization must be finite and in [0, 1]")
    if not math.isfinite(duration_s) or duration_s <= 0:
        raise ModelInputError("duration_s must be finite and > 0")
    positive = (params.input_voltage_v, params.conversion_efficiency,
                params.thermal_resistance_c_per_w,
                params.thermal_capacitance_j_per_c, params.fan_cooling_factor)
    if not all(math.isfinite(x) and x > 0 for x in positive):
        raise ModelInputError("voltage, efficiency, thermal constants and cooling factor must be > 0")
    if params.conversion_efficiency > 1:
        raise ModelInputError("conversion_efficiency must be <= 1")
    if not (math.isfinite(params.idle_power_w) and math.isfinite(params.max_power_w)
            and 0 <= params.idle_power_w <= params.max_power_w):
        raise ModelInputError("require 0 <= idle_power_w <= max_power_w")
    if not math.isfinite(params.ambient_temp_c):
        raise ModelInputError("ambient_temp_c must be finite")

    chip_power_w = params.idle_power_w + utilization * (params.max_power_w - params.idle_power_w)
    input_power_w = chip_power_w / params.conversion_efficiency
    input_current_a = input_power_w / params.input_voltage_v
    effective_rth = params.thermal_resistance_c_per_w / params.fan_cooling_factor
    steady_temp_c = params.ambient_temp_c + chip_power_w * effective_rth
    tau_s = effective_rth * params.thermal_capacitance_j_per_c
    start_temp_c = params.ambient_temp_c if previous_temp_c is None else previous_temp_c
    if not math.isfinite(start_temp_c):
        raise ModelInputError("previous_temp_c must be finite")
    decay = math.exp(-duration_s / tau_s)
    end_temp_c = steady_temp_c + (start_temp_c - steady_temp_c) * decay
    return {
        "evidence_class": "MODEL",
        "simulated": True,
        "calibrated_to_real_device": False,
        "model_version": "1.0.0",
        "inputs": {"utilization": utilization, "duration_s": duration_s,
                   "previous_temp_c": previous_temp_c},
        "assumptions": asdict(params),
        "outputs": {
            "chip_power_w": round(chip_power_w, 4),
            "input_power_w": round(input_power_w, 4),
            "input_current_a": round(input_current_a, 4),
            "ambient_temp_c": params.ambient_temp_c,
            "steady_state_temp_c": round(steady_temp_c, 4),
            "estimated_temp_c": round(end_temp_c, 4),
            "thermal_time_constant_s": round(tau_s, 4),
            "thermal_model": "first-order RC approximation",
        },
        "warning": "Illustrative values only; not a real sensor reading or device specification.",
    }


def simulate_profile(profile: list[dict[str, float]], params: ModelParams = ModelParams()) -> list[dict[str, Any]]:
    """Run a deterministic workload profile; each item has utilization and duration_s."""
    temp = params.ambient_temp_c
    reports = []
    for point in profile:
        report = simulate_step(point["utilization"], point["duration_s"], temp, params)
        temp = report["outputs"]["estimated_temp_c"]
        reports.append(report)
    return reports


if __name__ == "__main__":
    profile = [{"utilization": 0.1, "duration_s": 60},
               {"utilization": 0.5, "duration_s": 300},
               {"utilization": 1.0, "duration_s": 600}]
    print(json.dumps(simulate_profile(profile), indent=2))
