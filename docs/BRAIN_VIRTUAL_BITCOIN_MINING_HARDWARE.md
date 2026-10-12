# Electronic Brain — Initial Virtual Bitcoin Mining Hardware

## Scope

This is an initial, software-only foundation for representing Bitcoin ASIC mining hardware. It includes configurable generic ASIC profiles, hashboards/chip counts, a controller, PSU availability, network availability, fans, thermal estimates, simulated work counters, and fault injection.

It is **not** a complete emulation of every commercial miner. The starter profiles are illustrative estimates, not exact Antminer/WhatsMiner/Avalon SKU specifications. Add vendor-specific profiles only when backed by manufacturer documentation or measured data.

## Components represented

- ASIC miner profile: nominal hash rate, power, hashboard and chip counts.
- Hashboards: failure injection and proportional hash-rate reduction.
- PSU/controller/network: availability and fault states.
- Cooling: fan failures, PWM estimate, thermal response and thermal throttling indicator.
- Telemetry: estimated watts, temperature, hash rate and estimated joules per TH.
- Work counters: deterministic accepted/rejected simulated work units.
- Lifecycle: start, stop, tick and snapshots.

## Usage

```python
from brain_v12.virtual_hardware.mining_hardware import (
    DEFAULT_ASIC_PROFILES,
    VirtualASICMiner,
)

miner = VirtualASICMiner(DEFAULT_ASIC_PROFILES["asic_midrange"])
miner.start()
snapshot = miner.tick(seconds=10, inlet_temperature_c=27.0)
print(snapshot)
```

## Accuracy and safety boundaries

- The model never performs real Bitcoin mining and does not connect to a mining pool or wallet.
- No physical miner is controlled.
- Hash rate, power, temperature, fan PWM and efficiency are estimates, not calibrated readings.
- The model is functional/transaction-level, not chip-accurate, cycle-accurate, or a substitute for vendor firmware.
- The thermal equation is deliberately simple and should be replaced by calibrated parameters before operational planning.
- This model does not forecast profit or guarantee income.

## Initial validation

Run:

```bash
python -m unittest brain_v12.tests.test_mining_hardware -v
```

This is a first implementation layer intended for extension with vendor-documented profiles, persistent farm topology, network protocol simulation, and calibrated power/thermal models.
