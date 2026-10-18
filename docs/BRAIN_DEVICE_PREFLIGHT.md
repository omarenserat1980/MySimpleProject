# Brain Device Preflight (Read-Only)

## Purpose

Use one small Python standard-library script to collect comparable, privacy-conscious capability snapshots from Arkan (Windows), Redmi (Termux), and Realme (Android/Termux). This helps decide which bounded workloads a device may be considered for after independent identity and connectivity checks.

## Run locally

From the repository root:

```sh
python -m brain_v12.brain.device_preflight --alias redmi --output device-preflight-redmi.json
python -m brain_v12.brain.device_preflight --alias realme --output device-preflight-realme.json
python -m brain_v12.brain.device_preflight --alias arkan --output device-preflight-arkan.json
```

If module execution is not available in a checkout, run the file directly with Python. Copy only the resulting JSON report back for comparison. Review it before sharing.

## What it collects

- OS family/release and CPU architecture
- Python version and logical CPU count
- total memory when exposed by the OS
- free/total space for the current working volume
- presence/absence of a fixed allowlist of common tools

## Privacy and safety

- Uses Python's standard library only.
- No network probes, device-control commands, process enumeration, MAC/IP address collection, serial-number reads, environment-variable reads, or credential reads.
- Does not install packages, change settings, start services, or create cloud resources.
- Writes a file only if `--output` is explicitly supplied.
- Alias is a caller-provided label, not authenticated device identity.
- `report_sha256` is an accidental-change checksum only; it is not a digital signature, attestation, or proof that a report came from a particular device.
- `identity_verified`, `attestation_verified`, and `execution_eligible` always remain false. The report alone must never enable remote execution.

## Next acceptance gate

Compare the three reports, then separately prove each device's authenticated connection to the Brain control plane and bind it to a unique enrolled identity. A heartbeat alone is not identity proof. Do not use the Honda as a compute worker; keep it limited to explicitly authorized companion/information use. Cloud compute is eligible only after actual capacity and the zero-cost gate are independently verified.
