# BRAIN-ASIC-001 software board simulator

## Purpose
This is a zero-cost software bench for testing the Brain ASIC controller/reporting path before a physical board is obtained. It includes a software SHA-256d known-answer test and a simulated board/chip state report.

## Run on Android Termux or desktop
From the repository root:

```bash
python3 brain_v12/asic/unit_001/board_simulator.py
python3 brain_v12/asic/unit_001/board_simulator.py --json
python3 -m unittest brain_v12.asic.unit_001.test_board_simulator -v
```

The simulator uses only the Python standard library.

## Evidence boundary
- `SIMULATION_PASS` means only that the software known-answer vector and model checks passed.
- The simulated one-chip count and controller/thermal/power states are illustrative; they are not inventory or measured telemetry.
- Physical board/chip status remains `NOT_VERIFIED`.
- Hashrate, power, temperature, pool shares, payouts, and profit remain unknown/not measured.
- This tool does not connect to a pool, mine, or control hardware.
- Do not use simulated power/thermal values to wire or power a real board.

## Next real-hardware gate
When a board is actually received, record its make/model/revision, chip markings, photos and provenance. Then obtain the correct board schematic and manufacturer power specifications before any power-on testing. Keep simulated and physical evidence in separate records.
