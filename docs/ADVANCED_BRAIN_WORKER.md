# Advanced Brain Worker v1

## Purpose
An isolated worker lifecycle/admission primitive for Electronic Brain. It provides bounded leases, heartbeats, capability checks, fail-closed real-boot admission, and public status without a last-heartbeat timestamp.

## Modes
- `simulator`: default and safe for tests; cannot advertise `windows-server-2025-real-boot`.
- `real_executor`: explicit opt-in. This mode does not create trust or authorizations; it only accepts independently verified host facts.

## Real-boot admission gates
- `host_identity_verified`
- `kvm_runtime_verified`
- `executor_attestation_verified`
- `execution_contract_verified`
- `owner_authorized`
- `source_commit_matches`

Every gate must be explicitly true in the current host observation. A missing, false, or stale fact fails closed. This module does not manufacture facts, credentials, approvals, signatures, or attestations.

## Lifecycle
1. Create worker with a stable ID, declared capabilities, and explicit mode.
2. Register with an initial host observation.
3. Renew a bounded lease with heartbeat.
4. Evaluate task admission against a live lease and declared capability.
5. Send an admitted task to the existing authorized executor/gateway. This module itself never starts processes or VMs.

## Evidence boundaries
- Registration and heartbeat prove only worker lifecycle.
- `admitted=true` means policy gates passed, not that execution happened.
- `windows_boot_verified` is always false here. Real success requires guest-written Windows Server 2025 evidence and the repository's independent completion/proof gates.
- No cloud resources, paid services, physical devices, Windows VMs, or production credentials are created or touched by this module.

## Tests
```bash
python -m pytest brain_v12/tests/test_advanced_worker.py -q
```
