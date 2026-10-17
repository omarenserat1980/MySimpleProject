# BRAIN-ASIC-001 — Preliminary Component Identification Register

Status: PRELIMINARY — NOT A PROCUREMENT BOM, NOT FABRICATION-READY
Project owner/manufacturer designation: BRAIN AI (project label; legal registration and physical manufacturing are not verified)
Budget: JOD 0; no purchasing authorized.

## Purpose
This register identifies every hardware function required for a one-unit digital/physical prototype and defines what evidence is needed to select an exact component. It deliberately does not invent part numbers, voltages, footprints, or prices.

## Component register

| Ref | Function | Exact identity currently | Required selection evidence | Status |
|---|---|---|---|---|
| U1 | SHA-256d compute device | UNSELECTED | Exact chip/FPGA model, package, official datasheet, supply/interface limits | BLOCKED |
| U2 | Host/controller | UNSELECTED | Must match U1 serial/USB/SPI/UART/control protocol and firmware | BLOCKED |
| U3 | Core regulator(s) | UNSELECTED | Rail voltage, load current, transient response, sequencing from U1 data | BLOCKED |
| U4 | I/O regulator(s) | UNSELECTED | I/O bank/interface voltage and current requirements | BLOCKED |
| U5 | Input power protection | UNSELECTED | Input range, maximum current, surge/reverse polarity and thermal calculations | BLOCKED |
| U6 | Clock source | UNSELECTED | Required frequency, tolerance, load, startup and signal standard | BLOCKED |
| U7 | Reset/configuration circuit | UNSELECTED | Device-specific reset, boot/configuration and programming requirements | BLOCKED |
| U8 | Thermal sensor | UNSELECTED | Sensor interface, range, accuracy, placement and safe operating limits | BLOCKED |
| U9 | Fan driver / fan | UNSELECTED | Heat dissipation, airflow, voltage, current and control interface | BLOCKED |
| U10 | Host communications/ESD | UNSELECTED | Selected interface, cable, ESD and isolation requirements | BLOCKED |
| J1 | Power connector | UNSELECTED | Verified continuous current, conductor size, mating part and polarity | BLOCKED |
| J2 | Host connector | UNSELECTED | Selected protocol, pinout and mechanical constraints | BLOCKED |
| TP1+ | Test points | UNASSIGNED | Reviewed rail, reset, clock, debug and ground nets | BLOCKED |
| R/C/L | Passives | UNSELECTED | Values/ratings from datasheet, stability and signal-integrity calculations | BLOCKED |
| PCB1 | PCB substrate/layout | NOT CREATED | Reviewed schematic, stackup, verified footprints, ERC/DRC | BLOCKED |
| HS1 | Heat sink / thermal interface | UNSELECTED | Device package, dissipation, interface and measured thermal performance | BLOCKED |

## Reference-only candidate paths

### Path A: Existing BM1362 mining ASIC
The open-source emberOne/00 design is a reference project using BM1362. Its own project documentation describes a 12–24 V input hashboard and an external USB-connected controller; these values apply to that specific design only, not to a new BRAIN board. Exact BM1362 suffix compatibility must be checked against the reference documentation before considering any part.

Reference: https://github.com/256foundation/emberone00-pcb

Important: manufacturer documentation for the BM13xx family is not fully public; open-source protocol notes are reverse-engineered and must be treated as secondary evidence. Reference: https://github.com/256foundation/mujina/blob/main/mujina-miner/src/asic/bm13xx/REFERENCE.md

### Path B: Existing FPGA board
If the user already owns a specific FPGA board, use its exact board model and official schematic. This is the most practical zero-purchase path for digital RTL validation. It does not constitute a custom ASIC or a competitive Bitcoin miner.

### Path C: Custom silicon
A custom ASIC needs a compatible process design kit, physical-design and signoff flow, manufacturing acceptance, and fabrication. At JOD 0, this remains a simulation/design-research path, not an immediately manufacturable product.

## Selection gate
Do not select a chip or assign the rest of the BOM until one of these inputs is supplied:
1. exact model/part number of the board or chip already available; or
2. clear photos of both sides of the board and close-up photos of all main-chip markings; or
3. explicit selection of FPGA prototype and exact board model.

After identification, create:
- datasheet register with revision/source;
- pin and rail table;
- full exact-part-number BOM with footprints and quantity;
- reviewed schematic;
- KiCad PCB with ERC/DRC reports;
- assembly/position files and fabrication outputs only after approval.

## Evidence boundaries
- A reference design is not a BRAIN-manufactured product.
- The concept image is not CAD, a BOM, or a physical prototype.
- Simulated power and temperature are not measured hardware values.
- Do not report real hashrate, accepted pool shares, payouts, or profits without independently verifiable evidence.
- No purchase, paid service, production change, or fabrication order is authorized by this document.
