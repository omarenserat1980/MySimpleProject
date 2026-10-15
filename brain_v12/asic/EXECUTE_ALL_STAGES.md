# Brain ASIC: Execute All Available Stages

Run the actual RTL simulation and synthesis tools that are installed in the environment and save logs, generated netlist, SHA-256 hashes, tool versions, and a JSON execution report.

## Run locally

```bash
python brain_v12/asic/execute_asic_pipeline.py
```

Optional output directory:

```bash
BRAIN_ASIC_OUT=artifacts/asic-execution python brain_v12/asic/execute_asic_pipeline.py
```

The script uses Icarus Verilog (`iverilog` and `vvp`) for the repository RTL testbench and Yosys for synthesis. It does not silently install tools or provision paid services. GitHub Actions installs the open-source tools on its temporary runner.

## Evidence boundary

The report always keeps physical design, tapeout, foundry fabrication, and silicon test blocked. A synthesized netlist is not a placed-and-routed layout, a tapeout receipt, a manufactured die, or a lab test. Do not infer a physical chip from simulation or synthesis.

## Stages for future completion

- Physical design: a compatible PDK, timing constraints, floorplan, placement, clock-tree synthesis, routing, DRC and LVS are required.
- Tapeout: actual external submission and receipt are required.
- Fabrication: foundry-issued lot/wafer evidence is required.
- Silicon test: physical die/device identity, test setup, raw measurements and report are required.

Never invent these artifacts. Keep fabrication claims disabled until evidence is independently verified.
