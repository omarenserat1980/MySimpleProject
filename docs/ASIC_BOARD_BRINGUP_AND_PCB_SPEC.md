# BRAIN-ASIC-001 Physical Board Preparation and Bring-Up Gate

Status: **PREPARATION ONLY — NOT FABRICATION-READY**

This document prepares the engineering handoff for a real BRAIN-ASIC-001 board. It does not claim that a PCB has been laid out, fabricated, assembled, powered, or tested.

## Non-negotiable constraints

- Budget target: JOD 0; do not order parts, pay a fabrication service, activate hosted mining, or incur charges.
- Do not change production settings, create credentials, or put secrets in Git.
- Never invent chip identity, pinout, voltage, current, clock, thermal limits, connector wiring, hashrate, pool shares, or revenue.
- Keep simulated/digital evidence separate from physical-device evidence.
- Do not apply power until the exact fitted part and its datasheet establish the permitted power rails and pinout.

## Current physical-readiness status

| Gate | Status | Evidence needed |
|---|---|---|
| Exact compute device identified | BLOCKED | Manufacturer and complete top-marking / part number |
| Authoritative datasheet and package | BLOCKED | Datasheet URL or checked-in source citation, package drawing |
| Pinout and electrical limits | BLOCKED | Pin table, absolute maximum ratings, operating rails, I/O levels |
| Schematic | NOT CREATED | Reviewed schematic derived from the exact part datasheet |
| PCB layout | NOT CREATED | KiCad PCB, footprints matched to package drawings, design-rule checks |
| Power tree | BLOCKED | Rail/current budget and regulator design based on datasheet |
| Clock/reset/programming/debug | BLOCKED | Documented requirements for the exact device |
| Thermal/mechanical design | BLOCKED | Dissipation estimate, safe operating range, mounting and airflow plan |
| Assembly | NOT VERIFIED | BOM, assembly records, clear board photos |
| Bring-up | NOT VERIFIED | Current-limited first-power log and measured rail values |
| Compute function | NOT VERIFIED | Reproducible device-side SHA-256d test vectors and raw logs |
| Live pool mining | NOT VERIFIED | Authorized pool connection and independently verifiable accepted shares |
| Revenue | NOT VERIFIED | Payout evidence and independent transaction verification |

## Required design sequence

1. Identify the actual chip or FPGA by exact manufacturer part number and package marking.
2. Obtain the manufacturer's datasheet and confirm package/pinout, operating conditions, power sequencing, clock/reset, configuration, and thermal limits.
3. Decide whether the hardware is:
   - a control/interface board for an existing mining ASIC,
   - an FPGA development board implementing a testable SHA-256d datapath, or
   - a custom ASIC board.

   These are different designs and must not share an assumed pinout.
4. Produce a reviewed schematic and explicit power tree before PCB layout.
5. Create a KiCad project with verified footprints, board outline, connector mapping, net classes, and design rules.
6. Run electrical-rule checks and PCB design-rule checks; review the results rather than treating a successful tool exit as proof of correctness.
7. Only after the design is independently reviewed and a fabrication/assembly resource is available, consider manufacturing. No order is authorized by this document.
8. First power-up must use a current-limited bench supply with the board disconnected from any valuable host. Measure each rail and check for abnormal current/temperature before enabling the compute device.
9. Validate known SHA-256d vectors locally, then only test pool connectivity when a real supported miner/device interface exists and the user explicitly enables it.

## Zero-cost work that can proceed now

- Review and validate existing RTL and testbenches in CI.
- Prepare a pin-independent interface specification and a bill-of-materials template with unknowns marked TBD.
- Prepare a KiCad project skeleton only after choosing the exact hardware class; do not fabricate placeholder footprints or guessed pin mappings.
- Collect the device marking, board photos, connector labels, and available documentation.

## Evidence package required for a real board

Store redacted, non-secret evidence under a dedicated directory, for example:

- board-identity.json: board revision, device manufacturer/part number, package, evidence source.
- schematic.pdf and editable schematic source.
- pcb/ native layout files and exported fabrication files, only after review.
- bom.csv with exact part numbers and datasheet references.
- erc-report.txt and drc-report.txt.
- first-power-test.json: supply settings, measured rails/current, instrument identity, timestamp, operator notes.
- device-test-vectors.json and raw device-side logs.
- Photos of both board sides and the chip marking.

Never include access tokens, passwords, private keys, wallet secrets, or personal identifiers in the evidence package.

## Acceptance rule

The board is not physical-ready merely because RTL, a schematic, a KiCad project, synthesis, or CI passes. Mark each stage separately as NOT_STARTED, BLOCKED, PASS, or FAIL, and attach the corresponding evidence. Physical mining requires actual device-side computation and independently verifiable accepted shares; revenue requires payout evidence.

## Next blocking input

Provide a clear photo of both sides of the existing board and a close-up of the main chip marking, or provide the exact manufacturer part number. Until then, pinout, voltage, power components, footprints, and a fabrication-ready PCB remain intentionally blocked for safety.
