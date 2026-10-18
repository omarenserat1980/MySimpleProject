# Electronic Brain ASIC — Manufacturing Evidence Checklist

**Document ID:** EB-ASIC-EVIDENCE-002  
**Status date:** 2026-10-14  
**Repository:** `omarenserat1980/MySimpleProject`  
**Design RTL:** `brain_v12/asic/rtl/brain_asic_core.sv`

This checklist is intentionally conservative. Mark a box only after the corresponding evidence exists, is linked, and can be independently inspected. “Planned”, “configured”, and “workflow created” are not equivalent to “executed successfully”.

## Gate 0 — Design identity and reproducibility

- [ ] Record repository URL, branch, and full immutable commit SHA.
- [ ] Record SHA-256 of RTL, testbench, constraints, PDK config, and build scripts.
- [ ] Record top module, interface contract, reset/clock behavior, and intended function.
- [ ] Record the target foundry/process/PDK and the license/access basis for use.
- [ ] Pin tool/container versions and capture the exact commands.

**Gate result:** NOT RUN until the identity package is complete.

## Gate 1 — RTL simulation

- [ ] Confirm Icarus Verilog or another supported simulator is installed.
- [ ] Compile the exact source files at the recorded commit.
- [ ] Execute the compiled simulation (not compile-only).
- [ ] Verify all directed and randomized tests complete.
- [ ] Save the full log, simulator exit code, test seed/count, and pass marker.
- [ ] Upload artifacts to the same GitHub Actions run and record its URL/ID.

**Pass condition:** actual simulator exit code 0 and expected pass marker, with logs retained.  
**Blocked condition:** simulator absent, compile error, timeout, missing pass marker, or missing artifact.

## Gate 2 — Synthesis

- [ ] Run Yosys or an explicitly named synthesis tool.
- [ ] Confirm hierarchy/top-module checks pass.
- [ ] Save the synthesis script, complete log, exit code, and warnings.
- [ ] Save mapped netlist and cell/resource statistics.
- [ ] Confirm the target technology libraries and constraints are the intended ones.
- [ ] Hash all outputs and validate the manifest.

**Pass condition:** synthesis and required design checks complete without unexplained errors. A generic netlist is not a physical tape-out package.

## Gate 3 — Physical implementation and signoff

- [ ] Confirm compatible RTL-to-GDS flow and PDK are available.
- [ ] Complete floorplanning, placement, clock-tree synthesis, and routing.
- [ ] Save timing/electrical analysis and final metrics.
- [ ] Produce final GDSII and DEF/ODB outputs.
- [ ] Complete DRC and LVS, plus antenna and any process-required checks.
- [ ] Document every waiver and unresolved violation.
- [ ] Verify output hashes and archive full reports/logs.

**Pass condition:** all required checks completed and accepted for the selected PDK/process.  
**Blocked condition:** no supported PDK, incomplete routing, missing final GDS, or missing signoff reports.

## Gate 4 — Tape-out acceptance

- [ ] Record the foundry or shuttle provider and submission identifier.
- [ ] Preserve the dated submission receipt linked to the exact design revision.
- [ ] Preserve foundry intake/acceptance and DRC status.
- [ ] Record any required payment/booking evidence and any waivers.
- [ ] Verify the receipt independently through the provider's official channel.

**Pass condition:** provider-confirmed acceptance of the identified tape-out package.

## Gate 5 — Fabrication and package provenance

- [ ] Obtain provider confirmation that fabrication was completed.
- [ ] Record lot/wafer/die identifiers or equivalent traceable run information.
- [ ] Preserve packaging and shipment/custody documentation.
- [ ] Link the physical sample identity to the accepted design revision.
- [ ] Store photographs as supporting evidence only.

**Pass condition:** traceable external evidence of physical fabrication and sample provenance.

## Gate 6 — Silicon functionality

- [ ] Record the test board/fixture, instrument setup, voltage, clock, and environmental conditions.
- [ ] Execute a predeclared test plan on the physical sample.
- [ ] Preserve raw measurements, logs, failures, and pass/fail criteria.
- [ ] Confirm the sample identifier and revision match the fabrication evidence.
- [ ] Review electrical, timing, and intended-function results.

**Pass condition:** measured results on a traceable physical sample satisfy the declared criteria.

## Evidence record for each gate

Every gate record must contain:

- Gate name and status: `NOT_RUN`, `BLOCKED`, `PASS`, or `FAIL`.
- Commit SHA, workflow run ID/URL, timestamps, tool versions, and exact commands.
- Artifact paths, sizes, SHA-256 hashes, exit codes, and test/check results.
- Known limitations, skipped checks, assumptions, and waiver references.
- Reviewer name/role and review timestamp where a human review is required.

## Current status declaration

As of this checklist's creation, no boxes have been checked because this document does not itself execute or verify the flow. The known RTL source describes itself as a prototype and not fabricated hardware. Do not claim a physical ASIC exists or works until Gates 4–6 are supported by external, traceable evidence.
