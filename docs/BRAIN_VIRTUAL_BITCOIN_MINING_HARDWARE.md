# Electronic Brain — Initial Virtual Bitcoin Mining Hardware

## Scope

This is a starter software-only hardware foundation, not complete emulation of every commercial miner. It models generic ASIC devices and multi-node mining-farm orchestration for tests and planning. Vendor-specific profiles should only be added from manufacturer documentation or measured data.

## ASIC device model

`brain_v12/virtual_hardware/mining_hardware.py` represents configurable ASIC hash rate, power, hashboards/chip counts, PSU/controller/network availability, fans, temperature response, fault injection and simulated work counters. The initial three profiles are illustrative estimates, not exact Antminer/WhatsMiner/Avalon SKUs.

## Farm model

`brain_v12/virtual_hardware/mining_farm.py` provides node and rack inventory, multiple miner lifecycle operations, a local-only simulated job label, aggregate estimated hash rate/power/energy, node disable/enable, and event evidence. The simulated pool is only a label and never opens a socket or connects to a real mining pool.

## Usage

```python
from brain_v12.virtual_hardware.mining_farm import VirtualMiningFarm

farm = VirtualMiningFarm()
farm.add_miner("asic-01", rack_id="rack-01")
farm.add_miner("asic-02", rack_id="rack-01")
farm.start_all()
farm.assign_simulated_job("demo-job")
print(farm.tick(seconds=10))
```

## Accuracy and safety boundaries

- The model never performs real Bitcoin mining, connects to a mining pool, uses a wallet, or controls physical miners.
- Hash rate, power, temperature, fan PWM and efficiency are estimates, not calibrated readings.
- The model is functional/transaction-level, not chip-accurate, cycle-accurate, or a substitute for vendor firmware.
- The thermal equation is deliberately simple and should be replaced by calibrated parameters before operational planning.
- This model does not forecast profit or guarantee income.
- Complete commercial device emulation remains future work: exact ASIC chip topology, control-board firmware, board-level buses, fan curves, PSU electrical behavior, Stratum protocol behavior, and vendor-specific diagnostics have not been fully implemented.

## Validation

```bash
python -m unittest brain_v12.tests.test_mining_hardware brain_v12.tests.test_mining_farm -v
```
