# Advanced Brain Worker v1

## Purpose
An isolated worker lifecycle/admission primitive for Electronic Brain. It provides bounded leases, heartbeat renewal, capability checks, fail-closed real-boot admission, and public status without a last-heartbeat timestamp.

## Modes
- `simulator`: default and safe for tests; cannot advertise `windows-server-2025-real-boot`.
- `real_executor`: explicit opt-in. This mode does not create trust, authorizations, signatures, or attestations.

## Trusted real-boot gate verification
Real-boot admission requires an injected `gate_verifier` implementation supplied by trusted integration code. Each gate receives a proof object, the requested task, and worker identity. Missing verifier, missing proof, boolean claims, verifier exceptions, and any failed verification deny admission.

Required gates:
- `host_identity_verified`
- `kvm_runtime_verified`
- `executor_attestation_verified`
- `execution_contract_verified`
- `owner_authorized`
- `source_commit_matches`

The verifier must validate cryptographic signatures, expiry, audience, worker identity, task/commit binding, and authority using trusted keys and existing authorization services. Never implement the verifier by merely checking caller-provided booleans. The unit-test verifier is deliberately fake and must not be used in production.

## Lifecycle
1. Create worker with a stable ID, declared capabilities, explicit mode, and trusted verifier for real execution.
2. Register with fresh proof objects from trusted host and authority sources.
3. Renew a bounded lease with fresh proof objects.
4. Evaluate task admission against a live lease, declared capability, and verified evidence.
5. Send an admitted task to the existing authorized executor/gateway. This module itself never starts processes or VMs.

## Evidence boundaries
- Registration and heartbeat prove only worker lifecycle.
- `admitted=true` means policy gates passed, not that execution happened.
- `windows_boot_verified` is always false here. Real success requires guest-written Windows Server 2025 evidence and independent completion/proof gates.
- No cloud resources, paid services, physical devices, Windows VMs, or production credentials are created or touched by this module.

## Tests
```bash
python -m pytest brain_v12/tests/test_advanced_worker.py -q
```


## ChatGPT suggestion handoff

The authenticated endpoint `POST /api/brain/suggestions/{suggestion_id}/worker-candidate` converts a persisted suggestion into a **candidate only**. The caller supplies a requested `capability`; the endpoint uses the existing suggestion store and `evaluate_suggestion_handoff` policy.

Admission to this handoff requires:
- a known suggestion in `APPROVED` status;
- a source incident and supporting evidence;
- a test plan and rollback plan;
- an explicit target capability.

The endpoint does not enqueue or execute work, and always returns `execution_authorized=false` and `windows_boot_verified=false`. A request for `windows-server-2025-real-boot` is denied at this stage; it must go through the separate AdvancedWorker trusted-proof verifier and the existing authorized execution gateway. The ChatGPT model output itself is untrusted advisory data and never grants permission.

Example request body:
```json
{"capability":"diagnostics"}
```

Focused tests cover unapproved suggestions, missing evidence, missing rollback plans, and attempts to bypass real-boot gates. Run:
```bash
python -m pytest brain_v12/tests/test_advanced_worker.py brain_v12/tests/test_suggestion_worker_policy.py -q
```
