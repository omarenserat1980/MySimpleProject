# Electronic Brain V12 — ASIC and Digital Lab

## Brain Digital ASIC Lab

Run a real RTL simulator and logic synthesis locally or in a free GitHub Actions
runner. The tool does not fabricate hardware and never reports a pass when a
required EDA tool is absent.

```bash
python3 brain_v12/asic/digital_lab.py --output-dir artifacts/asic-digital-lab
```

The lab runs:

1. Icarus Verilog against `rtl/brain_asic_core.sv` and
   `rtl/tb_brain_asic_core.sv`, requiring the testbench marker
   `ALL_RTL_TESTS_PASSED`.
2. Yosys hierarchy/process/optimization/check/synthesis/check/stat passes.
3. JSON netlist generation and SHA-256 evidence.
4. A manifest with separate simulation and synthesis states, logs, source hashes,
   and explicit limitations.

The GitHub Actions workflow is `.github/workflows/brain-digital-asic-lab.yml`.
Open **Actions → Brain Digital ASIC Lab** and inspect the run and downloaded
`brain-digital-asic-lab-evidence` artifact.

## Evidence states

- `DIGITAL_ASIC_LAB_PASS`: real RTL testbench passed and Yosys produced a checked
  synthesized netlist in that run.
- `BLOCKED`: a required tool or input was unavailable.
- `FAIL`: a tool command, test, or evidence check failed.

This is a digital replacement for prototyping and exercising the RTL logic; it is
not a physical ASIC, FPGA execution, foundry signoff, or silicon fabrication.
