# Brain ASIC v1 — Cloud Build

Purpose: make the cloud server the primary ASIC development environment.

Pipeline:
1. SystemVerilog RTL
2. Icarus Verilog smoke verification
3. Yosys synthesis
4. JSON/netlist evidence
5. Future physical-design stage (OpenROAD/PDK) only after RTL gates pass

Important: this repository contains a real synthesizable RTL starting point, not a claim that silicon exists. A fabricated ASIC requires a compatible PDK, physical design, signoff, and a foundry.

Acceptance gates:
- RTL compiles
- Testbench passes
- Yosys synthesis completes
- No revenue is recorded from simulation
- No "ASIC physical" status until fabrication evidence exists
