# BRAIN-ASIC-001 Digital Simulation Contract

Date: 2026-10-17
Owner/manufacturer label: BRAIN AI (project designation; legal registration pending)
Product: BRAIN-ASIC-001
Status: DIGITAL SIMULATION SPECIFICATION — NOT A PHYSICAL DESIGN RELEASE
Budget ceiling: JOD 0

## Purpose

Define a reproducible software-only model for the pictured concept board. The model can validate control-flow, interface assumptions, thermal-sensor policy, and SHA-256d reference vectors without claiming the pictured components, board layout, electrical values, or performance exist physically.

## Model boundary

Included in the digital model:
- a logical compute-device block with explicit `SIMULATED` identity;
- power-state model: OFF, STARTING, READY, FAULT (logical states only; no voltage/current simulation unless calibrated parameters are later supplied);
- host-command interface model for submitting an 80-byte Bitcoin block header and nonce-range metadata;
- SHA-256d reference calculation and comparison against independent test vectors;
- thermal sensor abstraction with states AVAILABLE, UNAVAILABLE, and FAULT;
- event log with timestamp, model version, input vector hash, result, and evidence class;
- separate simulation evidence from physical-device, pool-share, payout, and revenue evidence.

Not included or not claimed:
- transistor-level ASIC simulation, foundry PDK, timing closure, silicon area, actual power consumption, PCB electrical validation, fabricated hardware, measured hashrate, pool acceptance, or income.

## Thermal policy

- In cloud/software simulation, a missing thermal sensor is allowed and recorded as NOT_APPLICABLE or UNAVAILABLE.
- For real hardware, sensor requirements are determined by the actual compute-device datasheet and the approved thermal safety design. If hardware safety requires a sensor and it is missing or faulty, block hardware operation.
- Never invent a temperature reading. Simulated temperatures must be labeled SIMULATED and must not be passed off as sensor measurements.

## Evidence classes

| Evidence class | Allowed conclusion | Forbidden conclusion |
|---|---|---|
| MODEL | Software state machine behaved as specified | Physical device exists or works |
| RTL_SIMULATION | RTL passed named tests in a named simulator | Chip was fabricated |
| SYNTHESIS | A netlist was produced with tool reports | Timing/power closure unless reports prove it |
| PCB_ERC_DRC | CAD checks passed for a specified revision | Board is electrically safe or manufactured |
| PHYSICAL_TEST | Actual device logs and instrument readings | Live mining or revenue unless separately proven |
| ACCEPTED_POOL_SHARE | Pool independently reports accepted work for identified worker/time | Profit or payout |
| VERIFIED_PAYOUT | Independently verifiable payment evidence | Ongoing profitability |

## Required test cases

1. SHA-256d known-answer vectors pass against an independent reference implementation.
2. Header byte order and nonce serialization are tested explicitly.
3. Target comparison covers below-target, equal-target, and above-target boundary cases.
4. Nonce-range model tests empty, single-value, end-boundary, and overflow/rejection cases.
5. Power-state model rejects commands while OFF, STARTING, or FAULT.
6. Thermal abstraction correctly handles sensor unavailable/fault without fabricating readings.
7. Every report contains `evidence_class`, `simulated: true`, model version, input hash, and test results.
8. No test can promote MODEL or RTL_SIMULATION into physical/mining/revenue evidence.

## Interface sketch (logical, not pin-level)

- `submit_header(header80_bytes, nonce_start, nonce_count)`
- `get_status()`
- `get_thermal_status()`
- `get_evidence_report()`

This interface is not a physical connector pinout and does not define voltages, current, timing, or board routing.

## Completion gates

- [ ] Implement model in a dedicated module, separate from physical-device drivers.
- [ ] Add deterministic unit tests and independent SHA-256d known-answer vectors.
- [ ] Run tests in CI and save raw logs plus JSON summary.
- [ ] Review that reports always label simulated values and cannot be mistaken for physical evidence.
- [ ] Only after identifying an actual device and authoritative datasheet, create a separate electrical schematic and PCB project with verified footprints.
- [ ] Require explicit authorization before any paid resource, fabrication order, pool connection, or production change.

## Truthful status

This document defines a simulation contract only. It does not claim that the concept image is a CAD file, that the PCB exists, that a custom ASIC has been manufactured, or that mining is active.
