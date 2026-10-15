# ASIC Physical Evidence Gate

This gate distinguishes executable RTL evidence from evidence of a physical chip. It does **not** claim that Brain ASIC has been fabricated.

## Lifecycle gates

1. RTL simulation: test log and passing test marker.
2. Synthesis: synthesized netlist and synthesis log.
3. Physical design: GDSII/OASIS layout plus DRC and LVS reports.
4. Tapeout: external submission receipt.
5. Foundry fabrication: foundry-issued receipt plus lot/wafer identifier.
6. Silicon test: test report, raw measurements, and device/die identifier.

Every artifact is hashed with SHA-256. External receipts also require issuer, issue date, and external reference. Hashes prove file integrity after capture, not that the contents are truthful; independently verify foundry and lab references.

## Manifest format

See `manifest.example.json`. Artifact paths are relative to the manifest directory. Each stage points to artifact keys in the `artifacts` object. Required keys are intentionally strict.

Run:

```bash
python3 tools/asic_physical_evidence_gate.py path/to/manifest.json --output evidence/audit.json
```

Exit code 0 means the available evidence is at least RTL-simulation-only or all physical stages have passed the file/metadata checks. Exit code 2 means evidence is incomplete or invalid. A complete audit is **not** independent proof of fabrication; the foundry and silicon-test artifacts must be checked against their issuers.

## Current policy

- Do not mark fabrication successful from RTL simulation, synthesis, or a generated layout alone.
- Do not fabricate receipts, serial numbers, wafer IDs, test results, or costs.
- Keep `fabrication_claim_allowed=false` until physical design, tapeout, foundry fabrication, and silicon test evidence are present and verified.
- Open-source tools and CI can generate RTL/synthesis evidence without a foundry budget. Fabrication and lab testing may require external services and funding.
