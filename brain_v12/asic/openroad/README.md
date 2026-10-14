# Bitcoin ASIC OpenROAD physical-flow experiment

This directory defines an initial, reproducible OpenROAD-flow-scripts experiment for the bounded nonce-search RTL on the pinned `sky130hd` platform.

- Flow source: OpenROAD-flow-scripts commit `9c431405a71909ca9aa5b9000d3d11fa36b2a32a`
- Workflow: `.github/workflows/brain-bitcoin-openroad-physical-flow.yml`
- Container: `openroad/flow-ubuntu22.04:latest`
- Design: `brain_bitcoin_nonce_search`

The SDC and floorplan values are initial engineering assumptions used to test flow integration, not reviewed timing constraints or tapeout signoff. The RTL is a reference design and may be too large or too slow for this initial platform flow. A green CI job is not by itself proof of timing closure, DRC/LVS closure, foundry signoff, fabricated silicon, Bitcoin mining, accepted pool shares, or revenue.

The workflow archives logs, reports, result files, and SHA-256 hashes even when the flow fails. Any GDS file is labelled only as a candidate artifact and requires independent validation before any stronger claim.
