# Bitcoin OpenROAD / PDK Readiness Gate

## Purpose

This gate pins and inspects the OpenROAD-flow-scripts (ORFS) SkyWater 130 nm high-density platform metadata before attempting technology mapping or physical implementation.

## Reproducible upstream revision

- Repository: https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts
- Commit: `9c431405a71909ca9aa5b9000d3d11fa36b2a32a`
- Platform candidate: `sky130hd`
- Checked inputs: platform config, standard-cell Liberty file, LEF directory, and GDS directory.

## Interpretation

A passing audit proves only that the pinned upstream platform metadata and selected files are present. It does **not** prove the OpenROAD executable is available, that the Bitcoin RTL is technology-mapped, that place-and-route ran, or that timing, DRC/LVS, GDSII, fabrication, mining, or revenue gates passed.

The workflow records the actual OpenROAD binary availability. If absent, the manifest explicitly reports `BLOCKED_NO_OPENROAD_EXECUTABLE`; it does not fabricate a physical-design pass.

## Next gate

Run a pinned OpenROAD-flow-scripts implementation against the actual `brain_bitcoin_nonce_search` RTL using this platform, after confirming all required PDK collateral and toolchain dependencies. Preserve synthesis, floorplan, placement, routing, timing, DRC/LVS (where supported), and output hashes as separate evidence.
