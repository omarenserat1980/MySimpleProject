# ASIC RTL-to-GDSII bring-up

This directory configures an initial open-source physical-design attempt for
`brain_v12/asic/rtl/brain_asic_core.sv` using OpenROAD Flow Scripts and the
SkyWater SKY130 HD platform.

## Run path

The GitHub Actions workflow `.github/workflows/asic-rtl-to-gds.yml`:
1. records the checked-out commit and RTL SHA-256;
2. fetches OpenROAD Flow Scripts;
3. stages the current RTL, this config, and the initial SDC;
4. runs the flow in the upstream `openroad/orfs` container;
5. retains logs, reports, results, and any generated GDSII as an Actions artifact.

The workflow uses only GitHub-hosted CI and open-source tools. It does not place
orders, provision paid cloud services, or submit files to a foundry.

## Evidence limits

A successful run may establish that a physical-design flow produced a GDSII
layout for this prototype. It does **not** by itself establish:
- foundry acceptance or a manufacturing-ready tapeout package;
- DRC/LVS signoff or complete timing/power signoff;
- that a wafer or die was fabricated;
- that a physical chip was delivered or tested.

The current RTL is a small ALU/datapath prototype, not a complete mining ASIC.
All constraints are initial estimates and must be reviewed against actual reports.
Never report fabricated silicon without independent foundry and lab evidence.

## Bitcoin nonce-search experiment

The separate workflow `.github/workflows/brain-bitcoin-openroad-physical-flow.yml` evaluates the bounded Bitcoin nonce-search RTL on the pinned `sky130hd` platform using a pinned OpenROAD-flow-scripts commit and a container image pinned by digest:

- Flow source: `9c431405a71909ca9aa5b9000d3d11fa36b2a32a`
- Container: `openroad/orfs@sha256:2979b97bd739d39e2369e76e3763a7b1a5de5e4d12b93d5511b42199031d57b8`
- Design: `brain_bitcoin_nonce_search`

This is an engineering experiment only. Initial SDC/floorplan values are not reviewed timing constraints or foundry signoff. A green workflow, synthesized netlist, or candidate GDS does not prove DRC/LVS closure, timing closure, fabricated silicon, Bitcoin mining, accepted pool shares, or revenue. Logs, reports, result files, and SHA-256 checksums are retained as evidence even when the flow fails.

