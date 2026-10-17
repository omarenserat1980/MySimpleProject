# BRAIN-ASIC-001 Schematic and PCB Completion Gate

Status: **ENGINEERING PLAN ONLY — NOT FABRICATION-READY**
Date: 2026-10-17
Budget ceiling: JOD 0; no purchases, hosted services, fabrication orders, or production changes authorized.

## Objective

Move BRAIN-ASIC-001 toward a reviewable electrical schematic and PCB without inventing electrical facts. This document establishes the design sequence and acceptance evidence. It is not a schematic, a PCB layout, or proof of physical hardware.

## Critical design decision: unresolved

The repository currently does not establish the exact compute device fitted to the intended board. Select exactly one path before assigning components or footprints:

1. **Existing mining ASIC reference board** — exact ASIC part number, package, official datasheet, and licensed/open reference design must be identified. BM1362 and BM1370 reference projects are different products; their pinouts, rails, clocks, and footprints must not be mixed.
2. **FPGA prototype** — exact FPGA development board/part, package, I/O bank voltages, clock source, configuration method, and power limits must be identified. This can test RTL but does not make a custom ASIC.
3. **Custom silicon ASIC** — requires a foundry-compatible process/design kit, synthesis and physical-design flow, timing/power closure, DRC/LVS, sign-off, tapeout acceptance, and manufacturing resources. A zero-budget simulation can prepare evidence but cannot establish fabrication readiness.

No path is silently selected by this document.

## Block-level architecture (concept only)

```text
[Protected input / connector]
          |
          v
[Input protection + power entry] ---> [Power rails / sequencing]
          |                                  |
          v                                  v
[Controller / host interface] <----> [Compute device]
          |                                  |
          +---------- status/debug ----------+
                         |
                    [Thermal sensing]
```

This is only a functional block diagram. It specifies no voltage, current, pinout, component value, footprint, or net assignment. Each block may change after the exact device and its datasheet are selected.

## Schematic completion checklist

- [ ] Record exact manufacturer, complete part number, package, and evidence source for the compute device.
- [ ] Archive the authoritative datasheet and record its revision/date.
- [ ] Create a pin table from the datasheet; independently review all power, ground, clock, reset, configuration, debug, and I/O pins.
- [ ] Calculate each rail's voltage/current budget from the datasheet and design conditions.
- [ ] Define input connector, reverse-polarity/overcurrent protection, regulator(s), power sequencing, decoupling, and test points from documented requirements.
- [ ] Define host/control interface and connector pin mapping.
- [ ] Define clock, reset, programming/debug, and boot/configuration circuitry.
- [ ] Define thermal monitoring and shutdown behavior based on device limits; do not assume a sensor is mandatory for a cloud simulation.
- [ ] Run KiCad ERC and resolve or explicitly justify every warning.
- [ ] Peer-review schematic and BOM before PCB layout.

## PCB completion checklist

- [ ] Use manufacturer/package-verified footprints only.
- [ ] Confirm board outline, connector/mechanical constraints, layer stack, copper weights, and manufacturing capabilities.
- [ ] Set net classes and trace/clearance rules from actual current, voltage, and fabricator capabilities.
- [ ] Route power and return paths with calculated widths; do not guess current capacity.
- [ ] Apply datasheet/layout guidance for decoupling, clocks, high-speed interfaces, thermal pads, and exposed copper.
- [ ] Run KiCad DRC and resolve or justify every warning.
- [ ] Inspect copper, return paths, clearances, assembly access, test points, and thermal/mechanical fit.
- [ ] Export Gerbers/drill files only after review; label them **DRAFT / NOT FOR FABRICATION** until all gates pass.
- [ ] Generate BOM and position files only from verified components and footprints.
- [ ] Require a separate explicit authorization before any paid fabrication or assembly.

## Acceptance evidence required

| Gate | Required evidence | Current status |
|---|---|---|
| Device identity | Clear marking/photo or verified exact part number | BLOCKED |
| Datasheet/pinout | Official source, revision, reviewed pin table | BLOCKED |
| Electrical schematic | Native KiCad schematic + ERC report | NOT CREATED / NOT VERIFIED |
| BOM and footprints | Exact part numbers, datasheet references, package match | BLOCKED |
| PCB layout | Native KiCad PCB + DRC report | NOT CREATED / NOT VERIFIED |
| Power/thermal analysis | Calculations based on documented limits | BLOCKED |
| RTL verification | Reproducible simulation logs and known SHA-256d vectors | NOT VERIFIED BY THIS DOCUMENT |
| Physical bring-up | Current-limited power log, measured rails, device-side test logs | NOT VERIFIED |
| Live mining | Independently verifiable accepted pool shares | NOT VERIFIED |
| Revenue | Verified payout evidence | NOT VERIFIED |

## Zero-cost work allowed now

- Validate and test the existing RTL with available free tools.
- Prepare the device-independent interface and evidence templates.
- Review open-source reference designs for engineering lessons, preserving their licenses and attribution.
- Inspect the user's existing board from clear photos and markings, if available.
- Build a KiCad project only after selecting an identified device path; keep all unknowns explicit rather than adding guessed footprints or electrical values.

## Safety and truthfulness rules

- Do not apply power to an unidentified board or chip.
- Do not copy voltages, pinouts, or component values from a different ASIC board.
- Do not describe a block diagram, RTL simulation, or generic KiCad file as a fabrication-ready electrical design.
- Do not claim that Brain has physically manufactured a chip or board without fabrication and device evidence.
- Simulated hashrate, shares, and earnings must never be presented as real.
- Budget remains JOD 0 unless the user explicitly authorizes a cost.

## Next blocking input

Provide one of:
- a clear photo of both sides of the actual board and a close-up of every main-chip marking; or
- the exact manufacturer part number and datasheet for the intended compute device; or
- an explicit selection of the FPGA prototype path with the exact board/part already available.

Until one of these is available, a safe, electrically correct, fabrication-ready schematic and PCB cannot be completed without guessing.
