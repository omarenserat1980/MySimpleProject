# ASIC identity evidence — safe status contract

Use `brain_v12/tools/asic_identity_evidence_v2.py`. It only enumerates host-visible USB metadata and optionally compares a serial with a separately supplied record. It does not send commands to the device or use the network.

A match is reported as `RECORD_SERIAL_MATCHED_REQUIRES_INDEPENDENT_REVIEW`, never as proof of physical silicon. Without a match, status is `PHYSICAL_IDENTITY_UNVERIFIED`. Strong identity requires independent manufacturer-signed attestation or equivalent authenticated device identity, a fresh challenge-response, and a device-origin execution test. Do not treat model strings, serial text, API health, simulator results, worker registration, or CI as proof of real ASIC hardware.

Run:
```bash
PYTHONPATH=. python -m unittest brain_v12.tests.test_asic_identity_evidence
python3 brain_v12/tools/asic_identity_evidence_v2.py --output asic-identity-report.json
```

This collector is read-only. It does not register hardware in Brain's software-only worker registry, merge, deploy, or change secrets.
