# ASIC physical identity evidence (read-only)

This tool is an evidence collector, not an ASIC simulator and not a hardware authenticator.

## Run
```bash
python3 brain_v12/tools/asic_identity_evidence.py
python3 brain_v12/tools/asic_identity_evidence.py --output asic-identity-report.json
```

It inventories host-visible USB and PCI devices without sending commands to a device or using the network. By default it returns `PHYSICAL_IDENTITY_UNVERIFIED`.

## Optional trusted record
Prepare a JSON record only after independently checking manufacturer documentation or an asset/attestation source:

```json
{
  "manufacturer": "Manufacturer name",
  "model": "Exact model",
  "serial": "Manufacturer-issued serial",
  "evidence_uri": "Reference to the independently reviewed evidence",
  "verified_by": "Reviewer or trusted verification process"
}
```

Then run:
```bash
python3 brain_v12/tools/asic_identity_evidence.py --trusted-record /secure/path/asic-record.json
```

A matching USB serial changes the report status to `PHYSICAL_IDENTITY_VERIFIED`, but that means only the record serial matched host enumeration. A human must still validate the evidence reference. USB/PCI strings and serials can be spoofed; strong proof requires manufacturer-signed attestation or another independently authenticated identity mechanism, plus a live device challenge and a separate execution/result test.

The report never treats a simulator, API health response, source code, CI pass, or worker registration as proof of physical ASIC hardware. No secrets should be placed in the report. The tool does not register devices in Brain's software-only worker registry, merge code, or deploy anything.
