# OpenLane 2 physical-design configuration

This directory configures a zero-budget CI attempt to run the existing
`brain_asic_core.sv` through the OpenLane 2 Classic RTL-to-GDSII flow using
the open-source SkyWater 130 nm `sky130A` PDK.

The CI job runs on a temporary GitHub-hosted runner and downloads open-source
tools/PDK data. No paid provider or physical fabrication is requested.

A run is considered successful only when OpenLane exits successfully and a
non-empty `.gds` output is found and recorded with its size and SHA-256 digest.
The retained artifact also contains the flow log and any discovered reports.

**Evidence boundary:** GDSII is a layout-data artifact. It does not prove tapeout
acceptance, wafer fabrication, packaged silicon, or operation of a physical chip.
