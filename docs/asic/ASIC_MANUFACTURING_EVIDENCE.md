# Electronic Brain ASIC — Verifiable Manufacturing Evidence

**Document ID:** EB-ASIC-EVIDENCE-001  
**Project:** Electronic Brain  
**Repository:** `omarenserat1980/MySimpleProject`  
**Design under review:** `brain_v12/asic/rtl/brain_asic_core.sv`  
**Status:** Evidence plan; not a certificate of fabrication  
**Last reviewed:** 2026-10-14

## 1. Purpose and claim boundary

This document defines the evidence required to verify each stage from RTL source through physical ASIC manufacturing. A passing software test, RTL simulation, synthesis report, or generated layout is evidence only for that specific stage. None alone proves that a physical chip was fabricated or is operational.

At the time this document was written, the source RTL identifies itself as an initial prototype and explicitly says it is not fabricated hardware. Therefore, **physical fabrication and silicon operation are not established by this document**.

## 2. Design identity

| Field | Value / required evidence |
|---|---|
| RTL top module | `brain_asic_core` |
| RTL source | `brain_v12/asic/rtl/brain_asic_core.sv` |
| Testbench | `brain_v12/asic/rtl/tb_brain_asic_core.sv` |
| Source revision | Record the full Git commit SHA used for every run |
| Source integrity | Generate SHA-256 hashes for all source, constraints, configuration, and PDK references |
| Target process / PDK | Must be explicitly selected and recorded; do not infer from generic RTL |
| Top-level integration | Not established until a chip-level wrapper, I/O, clock/reset, power intent, and constraints are reviewed |

## 3. Evidence stages and acceptance criteria

### Stage A — RTL simulation

Required artifacts:
- Exact RTL and testbench source at the tested commit.
- Tool name/version and complete compile/run commands.
- Full simulator log, exit code, and machine-readable summary.
- Test coverage listing directed cases, reset behavior, boundary values, and randomized tests (including seed and count).
- SHA-256 manifest tying artifacts to the run and commit.

Pass only when the simulator actually executes, exits with code 0, and emits the expected testbench pass marker. A workflow that cannot find a simulator is **BLOCKED**, not PASS.

### Stage B — Logic synthesis

Use Yosys or another named synthesis tool with a recorded version and reproducible script. Required artifacts:
- Synthesis script and tool versions.
- Full logs and exit status.
- Synthesized gate-level netlist (for example, JSON or Verilog).
- Cell/resource statistics and warnings.
- Successful hierarchy and design checks.
- Source-to-netlist hashes and run metadata.

A generic Yosys JSON netlist is evidence of synthesis only; it is not a foundry-ready physical design unless mapped against the selected process's libraries and constraints.

### Stage C — Physical implementation

Use a reproducible RTL-to-GDS flow such as LibreLane/OpenROAD with a supported PDK. Record the exact flow version, PDK version/license, configuration, constraints, and commit. Required artifacts include:
- Floorplan, placement, clock-tree, and routing reports.
- Final DEF/ODB and final GDSII layout.
- Timing and electrical reports, including setup/hold and relevant design constraints.
- DRC, LVS, antenna, and other required signoff reports.
- Final metrics and complete tool logs.
- SHA-256 hashes for all signoff outputs.

Acceptance requires the required signoff checks to complete with documented results. Missing reports, unrun checks, waived violations, or unsupported PDK configuration must be stated explicitly. A GDS file by itself does not establish signoff or manufacturing.

### Stage D — Tape-out / foundry handoff

Required evidence from the responsible organization:
- Foundry or shuttle provider identity and process/PDK.
- Accepted tape-out package identifier and timestamp.
- Submission receipt or portal confirmation that identifies the design revision.
- Foundry acceptance / DRC status and any waiver list.
- Purchase order, invoice, or shuttle booking where applicable, with sensitive commercial information redacted if shared publicly.

A local file named “GDSII” or a successful CI run is not a tape-out receipt.

### Stage E — Physical fabrication

Required external evidence:
- Foundry/shuttle confirmation that the submitted design was manufactured.
- Lot, wafer, die, or run identifier sufficient for independent confirmation (redact sensitive details only where appropriate).
- Fabrication/packaging completion record and shipment or custody record.
- Chip package photographs and markings as supporting evidence, not as sole proof.

Do not mark this stage PASS based solely on RTL, simulation, synthesis, GDS, or a self-authored status file.

### Stage F — Silicon bring-up and functional verification

Required artifacts:
- Physical sample identifier linked to the fabrication lot.
- Test fixture/board schematic, power and clock conditions, instrument identities/calibration status where relevant.
- Reproducible test procedure, raw logs, measured results, and pass/fail criteria.
- Evidence that the measured device is the fabricated design revision.
- Functional, electrical, timing, and reliability tests appropriate to the intended use.

A photo of a chip without traceable provenance and measured test results does not prove the chip works.

## 4. Evidence manifest format

For each run, publish a machine-readable manifest (JSON recommended) with these fields:

- `schema_version`
- `project`, `design_top`, `stage`, `status`
- `repository`, `git_commit`, `workflow_run_url`, `run_started_utc`, `run_finished_utc`
- `tool_versions`, `pdk_name`, `pdk_version`, `constraints_hash`
- `commands`, `exit_codes`, `pass_markers`
- `artifacts[]`: relative path, byte size, SHA-256, artifact role
- `checks[]`: check name, result, report path, waiver/reference if any
- `limitations[]`: unrun checks, assumptions, unsupported stages, blockers

The manifest must be generated from actual run outputs. Never fill in a PASS status, tool version, checksum, PDK, or manufacturing identifier by assumption.

## 5. Reproducibility and tamper-evidence

1. Pin the source commit and tool/container versions.
2. Keep raw logs and reports as immutable CI artifacts; retain the workflow run URL and run ID.
3. Calculate SHA-256 after each artifact is finalized and include it in the manifest.
4. Validate the manifest schema and recompute hashes in a separate verification step.
5. Preserve failures and blocked runs as evidence; do not replace them with synthetic success logs.
6. Link each artifact to the same commit and workflow run; if rerun, create a new evidence record.
7. Do not publish secrets, signing keys, private tokens, or unredacted commercial documents.

## 6. Suggested repository evidence layout

```text
docs/asic/
  ASIC_MANUFACTURING_EVIDENCE.md
  ASIC_DESIGN_SPEC.md
  ASIC_VERIFICATION_PLAN.md
  ASIC_TAPEOUT_CHECKLIST.md
  evidence/
    README.md
    manifest.schema.json
    runs/<workflow-run-id>/
      manifest.json
      rtl-simulation.log
      synthesis.log
      synthesis-statistics.txt
      physical-signoff-summary.json
      checksums.sha256
```

Only include artifacts that actually exist. If a stage has not run, record it as `NOT_RUN` or `BLOCKED`; do not create placeholder logs that look like execution evidence.

## 7. Independent verification commands

Examples for a downloaded evidence bundle:

```bash
# Verify artifact hashes against the published checksum file
sha256sum -c checksums.sha256

# Record the exact source revision
git rev-parse HEAD

# Record tool versions (only for installed tools)
iverilog -V
vvp -V
yosys -V
verilator --version
```

A missing command should be reported as unavailable; it must not be silently skipped and then counted as a successful check.

## 8. Public references

- Yosys synthesis documentation: https://yosyshq.readthedocs.io/projects/yosys/en/latest/using_yosys/synthesis/synth.html
- Yosys synthesis example and netlist outputs: https://github.com/YosysHQ/yosys/blob/main/docs/source/getting_started/example_synth.rst
- OpenLane physical-design flow and outputs: https://openlane2.readthedocs.io/en/latest/getting_started/newcomers/index.html
- OpenLane signoff overview: https://openlane.readthedocs.io/en/2023.09.07/flow_overview.html

## 9. Current conclusion

**Current verified claim:** the repository contains an RTL prototype and testbench source.  
**Not established by this document:** successful fresh simulation, completed synthesis, signoff-clean GDSII, accepted tape-out, physical fabrication, packaged silicon, or functioning hardware.

Update this conclusion only when the corresponding evidence artifacts are available and independently checkable.
