"""Brain-native bioelectric concept simulator.

This module models a stack of idealized electrocytes for education and
software-only planning. It does not access hardware, measure electricity,
control a device, or claim real energy production or revenue.
"""
from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class BioelectricSimulation:
    status: str
    evidence_class: str
    real_electricity_verified: bool
    revenue_verified: bool
    cells_in_series: int
    parallel_strings: int
    cell_voltage_v: float
    cell_internal_resistance_ohm: float
    load_resistance_ohm: float
    pulse_duration_s: float
    pulses_per_second: float
    open_circuit_voltage_v: float
    equivalent_internal_resistance_ohm: float
    load_current_a: float
    load_voltage_v: float
    load_power_w: float
    energy_per_pulse_j: float
    modeled_average_power_w: float
    notes: tuple[str, ...]


def simulate_bioelectric_node(
    *,
    cells_in_series: int = 100,
    parallel_strings: int = 10,
    cell_voltage_v: float = 0.15,
    cell_internal_resistance_ohm: float = 1000.0,
    load_resistance_ohm: float = 1000.0,
    pulse_duration_s: float = 0.1,
    pulses_per_second: float = 1.0,
) -> BioelectricSimulation:
    """Return a theoretical estimate; never marks simulated output as real."""
    integer_values = {
        "cells_in_series": cells_in_series,
        "parallel_strings": parallel_strings,
    }
    for name, value in integer_values.items():
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 1_000_000:
            raise ValueError(f"{name} must be an integer between 1 and 1000000")

    numeric_values = {
        "cell_voltage_v": cell_voltage_v,
        "cell_internal_resistance_ohm": cell_internal_resistance_ohm,
        "load_resistance_ohm": load_resistance_ohm,
        "pulse_duration_s": pulse_duration_s,
        "pulses_per_second": pulses_per_second,
    }
    for name, value in numeric_values.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"{name} must be a finite number")
    if cell_voltage_v <= 0:
        raise ValueError("cell_voltage_v must be greater than zero")
    if cell_internal_resistance_ohm < 0:
        raise ValueError("cell_internal_resistance_ohm cannot be negative")
    if load_resistance_ohm <= 0:
        raise ValueError("load_resistance_ohm must be greater than zero")
    if pulse_duration_s <= 0:
        raise ValueError("pulse_duration_s must be greater than zero")
    if pulses_per_second < 0:
        raise ValueError("pulses_per_second cannot be negative")

    voltage = cells_in_series * float(cell_voltage_v)
    internal_resistance = (
        cells_in_series * float(cell_internal_resistance_ohm) / parallel_strings
    )
    current = voltage / (internal_resistance + float(load_resistance_ohm))
    load_voltage = current * float(load_resistance_ohm)
    load_power = current * current * float(load_resistance_ohm)
    energy_per_pulse = load_power * float(pulse_duration_s)
    average_power = energy_per_pulse * float(pulses_per_second)
    if not all(math.isfinite(value) for value in (voltage, internal_resistance, current, load_voltage, load_power, energy_per_pulse, average_power)):
        raise ValueError("parameters produce a non-finite estimate; reduce the input values")

    return BioelectricSimulation(
        status="SIMULATED_ONLY",
        evidence_class="MODEL_ESTIMATE",
        real_electricity_verified=False,
        revenue_verified=False,
        cells_in_series=cells_in_series,
        parallel_strings=parallel_strings,
        cell_voltage_v=float(cell_voltage_v),
        cell_internal_resistance_ohm=float(cell_internal_resistance_ohm),
        load_resistance_ohm=float(load_resistance_ohm),
        pulse_duration_s=float(pulse_duration_s),
        pulses_per_second=float(pulses_per_second),
        open_circuit_voltage_v=voltage,
        equivalent_internal_resistance_ohm=internal_resistance,
        load_current_a=current,
        load_voltage_v=load_voltage,
        load_power_w=load_power,
        energy_per_pulse_j=energy_per_pulse,
        modeled_average_power_w=average_power,
        notes=(
            "All output values are theoretical estimates, not physical measurements.",
            "No hardware, network, battery, or external service is accessed.",
            "Real generation requires a physical source and independent voltage/current measurements.",
            "Revenue remains unverified and is never inferred from modeled power.",
        ),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cells-in-series", type=int, default=100)
    parser.add_argument("--parallel-strings", type=int, default=10)
    parser.add_argument("--cell-voltage-v", type=float, default=0.15)
    parser.add_argument("--cell-resistance-ohm", type=float, default=1000.0)
    parser.add_argument("--load-resistance-ohm", type=float, default=1000.0)
    parser.add_argument("--pulse-duration-s", type=float, default=0.1)
    parser.add_argument("--pulses-per-second", type=float, default=1.0)
    args = parser.parse_args()
    result = simulate_bioelectric_node(
        cells_in_series=args.cells_in_series,
        parallel_strings=args.parallel_strings,
        cell_voltage_v=args.cell_voltage_v,
        cell_internal_resistance_ohm=args.cell_resistance_ohm,
        load_resistance_ohm=args.load_resistance_ohm,
        pulse_duration_s=args.pulse_duration_s,
        pulses_per_second=args.pulses_per_second,
    )
    print(json.dumps(asdict(result), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
