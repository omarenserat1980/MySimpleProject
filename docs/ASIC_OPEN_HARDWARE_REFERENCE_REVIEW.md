# BRAIN-ASIC-001 Open Hardware Reference Review

Status: REFERENCE STUDY ONLY — NOT A BRAIN PCB RELEASE

Reviewed public reference repositories on 2026-10-17. These designs are examples to learn from, not proof that BRAIN-ASIC-001 exists physically and not a recommendation to apply power to an unidentified board.

## Reference A: emberOne/00 hashboard

Repository: https://github.com/256foundation/emberone00-pcb

The repository describes a roughly 100 W open-source hashboard based on the Bitmain BM1362, with a stated 12–24 V DC input and a separate USB-connected control board. It includes KiCad schematic/PCB sources and manufacturing files. The README distinguishes tested BM1362 variants and explicitly warns that some variants are untested or incompatible.

Usefulness:
- Demonstrates a hashboard plus separate controller architecture.
- Offers editable KiCad project files and assembly notes.
- Its stated voltage and power apply only to that design, not to BRAIN-ASIC-001 or any unidentified board.

Risks / limitations:
- Requires the exact compatible BM1362 variant, correct assembly and a supported controller/firmware.
- Not a zero-cost physical build: ASIC, components, PCB, stencil, assembly and suitable power/cooling are still required.
- Do not copy its pinout, BOM, power rails, footprints or connector mapping into a different chip design.

## Reference B: Bitaxe Gamma

Repository: https://github.com/bitaxeorg/bitaxeGamma

The repository contains KiCad schematic/PCB and manufacturing files for a single-BM1370 Bitcoin miner. Its README states that the ASIC footprint/pinout differs from earlier Bitaxe chip families and warns that the device is sensitive to power and cooling. The reference design specifies a 5 V input with a current requirement above 4 A; these details apply to the Gamma board only.

Usefulness:
- Shows a compact, integrated controller-plus-ASIC design.
- Provides firmware, PCB, BOM and build documentation as a reference.
- Illustrates why chip-family identity, power input, thermal design and firmware support must be treated as one verified design.

Risks / limitations:
- BM1370 is not interchangeable with BM1362; their footprints and pinouts differ.
- Its input voltage and connector must never be copied onto an unrelated board.
- Its public hashrate descriptions are design-specific and are not evidence of BRAIN performance or revenue.

## Decision for Brain

Do not start a new custom silicon/tapeout path under a zero-dinar budget. First validate the existing digital SHA-256d RTL independently. If a physical mining demonstration is the near-term goal, evaluate a known open hardware reference as a separate, explicitly named reference platform; do not relabel it as Brain-manufactured hardware.

Before selecting a physical platform, capture:
1. Clear photographs of the actual available board, front and back.
2. Exact main-chip marking and board revision.
3. Connector labels and any existing documentation.
4. Whether the board is already assembled and whether a known-good power source is available.

Then identify the exact device and its manufacturer documentation. Only after this may a board-specific schematic, power tree, interface and bring-up checklist be selected.

## Evidence and budget policy

- Target budget remains JOD 0; no parts or services are ordered by this review.
- No unknown chip pinout, voltage, current, clock or temperature limit may be guessed.
- Simulation, synthesis, published reference hashrate, and CI success are not physical-device evidence.
- Real mining requires device-side operation plus independently verifiable accepted pool shares. Real revenue requires independent payout evidence and actual power/cost measurements.
- The current canonical manifest remains authoritative for BRAIN-ASIC-001 status: physical fabrication, device operation, live mining and revenue are NOT VERIFIED.
