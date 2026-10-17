# Physical ASIC Evidence Gate

## Current decision

**BLOCKED / NOT VERIFIED** until a physical device and its evidence are actually available.
The existing SystemVerilog, Icarus/VVP runs, Yosys netlist, and Python logic simulator
prove software/RTL behavior only. They do not prove fabricated silicon or a connected FPGA.

## Required evidence bundle

Create `artifacts/asic/physical-evidence/` on a machine connected to the real device:

- `device_attestation.json`: device type (ASIC or FPGA), manufacturer, part number,
  serial number, interface, exact probe command, successful exit code, UTC capture time,
  raw probe log filename and SHA-256, and independent evidence references.
- `probe-output.txt`: unedited output captured from the actual device probe.
- `bringup_test.json`: test identifier, input vector, expected and observed output,
  serial number, UTC timestamp, raw log filename and SHA-256.
- `bringup.log`: unedited output of a test executed on the connected device.
- For ASIC specifically: foundry, wafer lot, die/package identifiers, and a manufacturing
  or production-test report that can be independently checked.

Use the checker:

```bash
python brain_v12/asic/physical_hardware_gate.py --evidence-dir artifacts/asic/physical-evidence
```

The checker fails closed when evidence is absent or inconsistent. A structurally valid bundle
is still only **pending independent review**; it does not authenticate the device or its origin.
Never fill these fields with simulated, guessed, or copied example values.

## Meaning of statuses

- `BLOCKED_PHYSICAL_EVIDENCE_MISSING`: no real device evidence bundle supplied.
- `REJECTED_OR_INCOMPLETE`: required fields/logs/hashes/tests are absent or inconsistent.
- `EVIDENCE_BUNDLE_STRUCTURALLY_VALID_REQUIRES_INDEPENDENT_REVIEW`: structure and hashes pass,
  but physical authenticity is **not** automatically verified.
- `PHYSICAL_HARDWARE_VERIFIED`: may only be assigned after an independent reviewer verifies the
  actual device, provenance, and live test. This script intentionally never emits this status.

No purchase, paid cloud provisioning, or device operation is authorized by this gate.
