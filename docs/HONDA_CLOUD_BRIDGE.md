# Honda Cloud Bridge for Electronic Brain

Status: **Planning module and tests added on the feature branch; not merged, deployed, or connected to a vehicle.**

## Purpose

Add cloud-assisted capabilities around the Honda vehicle profile without modifying the vehicle's ECU, head unit, or firmware. The vehicle's exact model/year/head-unit combination must be verified before profile-specific instructions are enabled. Brain's earlier notes mention both Honda N-BOX and Honda e:NP1/Honda CONNECT 3.0; these are kept as separate profiles and must not be conflated.

## Cloud components

| Component | Role | Default |
|---|---|---|
| Vehicle Profile Registry | Stores normalized model/year/head-unit metadata and verification status | Local / unverified |
| Firmware Metadata Verifier | Reads update manifests, computes SHA-256, records version and source evidence | Read-only |
| Evidence Vault | Stores diagnostic reports, manifest hashes, timestamps, and build/test evidence | Local-only |
| Health Alert Relay | Relays opt-in status or integrity alerts without vehicle control | Disabled |
| Cloud Executor | Runs bounded metadata checks or report processing on already-authorized free capacity | Disabled |

## Guardrails

- No paid cloud resource is created or enabled without explicit user approval and an accepted budget.
- Cloud sync is off by default; this module only generates a plan and makes no network calls.
- Never upload a raw VIN; if a VIN is needed for correlation, use its SHA-256 fingerprint and minimize retention.
- Never issue remote vehicle commands or install firmware automatically.
- Do not treat a checksum alone as proof that firmware is authentic. Validate the source/signature and exact model compatibility before advising an update.
- Do not assume YouTube playback is supported by Honda CONNECT; compatibility depends on the exact head unit, region, model year, and approved interfaces.
- The GitHub repository/Actions can hold code and bounded build evidence, but an artifact is not a durable vehicle telemetry database and may expire.
- A CI pass proves only the tested software behavior. It does not prove a live connection to the car or phone.

## Implementation

The module at brain_v12/brain/honda_cloud_components.py provides:
- HondaVehicleProfile for minimal profile metadata.
- HondaCloudPolicy with zero-cost defaults and hard rejection of remote vehicle commands and automatic firmware installation.
- fingerprint_vin() and evidence_digest() for privacy-aware correlation and evidence integrity.
- plan_honda_cloud_components() to return a deployment plan without provisioning services or making network calls.

Tests: brain_v12/tests/test_honda_cloud_components.py.

## Safe activation sequence

1. Verify whether the vehicle is Honda N-BOX or Honda e:NP1, then confirm model year and head-unit version from the vehicle's own settings/labels.
2. Keep the cloud policy disabled while building and testing locally.
3. Review the CI test results and security review on the feature branch.
4. Enable only a selected evidence destination after the user explicitly approves the provider and data retention.
5. Confirm a real authenticated upload with a test report before calling the bridge active.

No cloud service, account, billing, vehicle pairing, or firmware installation is activated by this implementation.
