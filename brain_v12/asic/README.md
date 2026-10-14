# Electronic Brain V12 — Advanced ASIC Complex (prototype)

## Current scope

This directory starts a hardware-description-language (RTL) prototype alongside
the existing Python software-only logic simulator. The RTL file is a synthesizable
parameterized ALU/datapath register candidate; it is not proof of synthesis,
physical implementation, FPGA availability, or manufactured silicon.

## Artifacts

- `rtl/brain_asic_core.sv`: parameterized arithmetic/logic datapath with a
  registered result and zero flag.
- `hardware/BOM.csv`: preliminary hardware bill-of-materials and evidence states.
- `hardware/ASSEMBLY_PLAN.md`: staged physical-prototype plan and explicit gates.

## Toolchain gate

Before claiming RTL simulation or synthesis, check whether an appropriate tool
(e.g. Verilator or Icarus Verilog for simulation; Yosys for synthesis) is installed
and record its actual version and command result. Tool absence means
`NOT_ASSESSED`/blocked, not pass. Do not install software, purchase hardware,
or provision a paid service without explicit approval.

## Evidence states

- `NOT_STARTED`: not attempted.
- `IN_PROGRESS`: work in progress.
- `SIMULATED_PASS`: actual simulator run passed.
- `VERIFIED_BUILD`: defined build/synthesis checks passed with retained evidence.
- `PHYSICAL_HARDWARE_VERIFIED`: physical device was actually tested and evidence reviewed.

Design intent and static source inspection do not qualify as simulation or synthesis.
Never report `PHYSICAL_HARDWARE_VERIFIED` based on the software simulator.

## Software-node compiler (initial milestone)

`node_compiler.py` compiles a strict JSON graph into combinational SystemVerilog.
It supports add, subtract, bitwise AND/OR/XOR, NOT, pass-through, and constants.
Node references must target inputs or earlier nodes; malformed graphs fail closed.
This initial milestone intentionally does not generate sequential logic, pin
constraints, board-specific programming files, or foundry-ready ASIC layouts.

Example:

```bash
python -m brain_v12.asic.node_compiler \
  --spec brain_v12/asic/examples/adder.json \
  --output artifacts/asic/brain_adder.sv
```

A `DESIGN_GENERATED` result means only that validated RTL text was emitted.
Run `python -m brain_v12.asic.toolchain_probe` to discover local RTL tools,
then use the existing CI flow for simulation/build evidence. Never promote
generated RTL to `SIMULATED_PASS`, `VERIFIED_BUILD`, or physical verification
without the corresponding actual run and retained evidence.

## Existing simulator

The existing API remains the software-only model:
- `GET /api/asic-sim/status`
- `POST /api/asic-sim/run`

Keep software simulation, RTL simulation, synthesis, FPGA execution, and silicon
validation as separate evidence levels.
