# Bitcoin ASIC Physical Design Gate

## Purpose

This gate advances the bounded Bitcoin nonce-search RTL toward an open-source ASIC flow without overstating what generic synthesis proves.

## Current automated preflight

Workflow: `.github/workflows/brain-bitcoin-asic-physical-design-readiness.yml`

It runs Yosys hierarchy checks, process lowering, optimization, generic synthesis, netlist validation, and evidence hashing. The artifact includes the generic netlist, synthesis log, and a manifest with SHA-256 checksums.

A green run means **generic synthesis preflight passed only**. It does not mean a foundry-specific implementation is complete.

## Required next gates

1. **Technology and PDK selection:** choose an open PDK and exact process corner; record license, version, and source revision.
2. **Technology mapping:** map the design to the PDK's standard-cell library; archive the mapped netlist and cell statistics.
3. **Constraints:** define clock period, input/output delays, reset assumptions, and false/multicycle paths with rationale.
4. **Floorplan and place-and-route:** run a compatible OpenROAD flow with the chosen platform files; preserve logs, configuration, and database snapshots.
5. **Timing and physical checks:** inspect setup/hold timing, congestion, utilization, DRC/LVS where supported, and unresolved violations.
6. **GDSII evidence:** require a non-empty GDSII output, tool logs, source/configuration revisions, and SHA-256 checksums. Do not call it tapeout-ready without foundry-specific signoff.
7. **Hardware and mining evidence:** silicon fabrication/testing and mining-pool accepted shares are separate gates and are not established by RTL or GDSII alone.

## Explicit non-claims

This preflight does not establish PDK-backed mapping, placement, routing, timing closure, DRC/LVS closure, GDSII production, fabricated silicon, pool connectivity, accepted shares, Bitcoin rewards, or revenue.

## Reproducibility

The workflow uploads its evidence artifact for 14 days. Preserve the artifact and manifest externally if a longer audit trail is required.
