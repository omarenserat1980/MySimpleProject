# BRAIN-ASIC-001 — Hardware Identification and BOM Definition

Status: **PRELIMINARY ENGINEERING BOM — NOT ORDERABLE / NOT FABRICATION-READY**
Date: 2026-10-17
Project designation: BRAIN AI / Electronic Brain
Budget ceiling: JOD 0; no purchase or fabrication authorized.

## Critical distinction

The existing repository defines SHA-256d RTL and a concept-board direction, but it does not identify a verified ASIC device that Brain has manufactured. Therefore a safe, complete part-number-level BOM cannot be honestly finalized until the compute-device path is chosen. Do not order components using guessed values.

## Choose one of three hardware paths

### Path A — Use an existing mining ASIC chip
Required before schematic:
- exact manufacturer and full chip part number;
- authoritative datasheet revision and package drawing;
- confirmed pinout, operating rails, sequencing, clock/reset/configuration interface;
- legitimate supply/source and assembly feasibility;
- matching reference schematic/PCB with applicable license.

Without these, chip footprint, rails, regulator part numbers, decoupling, and routing are **TBD / BLOCKED**.

### Path B — FPGA prototype (best for zero-cost logical verification if an existing board is available)
Required:
- exact FPGA board already available to the user, or exact FPGA part and package;
- official board schematic and reference manual;
- supported free synthesis/simulation toolchain;
- verified I/O voltage and clocking constraints.
An FPGA prototype can validate portions of SHA-256d RTL; it is not a custom ASIC and is not equivalent to a competitive Bitcoin miner.

### Path C — Custom ASIC
Requires a suitable process design kit, synthesis/physical design, DRC/LVS, timing/power sign-off, tapeout acceptance, and a foundry/manufacturing path. This is not realistically fabrication-ready under JOD 0. RTL alone is not a manufactured ASIC.

## Preliminary functional BOM (identifiers intentionally not invented)

| Ref | Functional item | Required definition | Part number | Status |
|---|---|---|---|---|
| U1 | Compute device | ASIC or FPGA exact package, datasheet and interface | TBD | BLOCKED |
| U2 | Controller / host bridge | Depends on U1 interface and chosen architecture | TBD | BLOCKED |
| U3 | Power regulator(s) | Rails/current derived from exact datasheets | TBD | BLOCKED |
| U4 | Input protection | Input range, reverse polarity, surge and current limits | TBD | BLOCKED |
| U5 | Thermal sensor | Exact sensor/interface; optional in cloud simulation, safety-dependent on real hardware | TBD | BLOCKED |
| U6 | Clock source | Frequency/tolerance/load derived from device spec | TBD | BLOCKED |
| J1 | Power connector | Current rating and footprint from verified power budget | TBD | BLOCKED |
| J2 | Host/data connector | Interface, pinout and ESD requirements | TBD | BLOCKED |
| TP1… | Test points | Rails, reset, clock, debug chosen from reviewed schematic | TBD | BLOCKED |
| HS1/FAN1 | Heat sink/fan | Dissipation and thermal resistance based on device measurements/specs | TBD | BLOCKED |
| PCB1 | Bare PCB | Stackup, copper, clearances, dimensions and verified footprints | TBD | NOT DESIGNED |
| R/C/L | Passives | Values and ratings from datasheet/reference design calculations | TBD | BLOCKED |

## Minimum evidence to turn this into a fully identified BOM

1. Select path A, B, or C.
2. For A or B, provide the exact device/board part number or a clear photo of both sides plus close-up chip markings.
3. Verify official datasheet, package, pinout, electrical limits and reference design.
4. Build the schematic with exact part numbers and footprints.
5. Calculate power and thermal limits, then complete ERC/DRC.
6. Generate BOM, assembly/position files, Gerbers and drill files only after review.
7. Run tests and keep simulation results separate from physical evidence.

## Safety and evidence rules

- Never power an unidentified board.
- Do not mix BM1362, BM1370, FPGA, or custom-silicon pinouts/voltage assumptions.
- Never use concept-art components as a procurement specification.
- Do not claim fabrication, real hashrate, accepted shares, payouts, or profit without independent evidence.
- Simulation-only work must label every computed electrical/thermal value as SIMULATED.
- No purchases, paid services, cloud charges, or production changes without explicit user authorization.

## Immediate next step

Reply with one of: **A — existing mining ASIC**, **B — FPGA prototype**, or **C — custom ASIC**. If a board/chip is already physically available, provide its exact part number or photos. Until then, a fully identified part-by-part shopping list would require unsafe guessing.
