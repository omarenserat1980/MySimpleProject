# Cloud Executor Activation

The production Windows executor is a Brain-owned Linux x86_64 cloud VM.

## Activation

On the cloud VM, provide these host environment values:

- `BRAIN_CLOUD_EXECUTOR=1`
- `BRAIN_CLOUD_EXECUTOR_ID`
- `BRAIN_CLOUD_EXECUTOR_ID`: choose this before requesting the attestation.
- `BRAIN_CLOUD_EXECUTOR_ATTESTATION_B64`: base64-encoded JSON attestation signed by the trusted provisioning service.
- `BRAIN_CLOUD_EXECUTOR_ATTESTATION_PUBLIC_KEY_B64`: trusted Ed25519 public key.

The signed payload must bind the exact executor ID, `hostname`, and `architecture=x86_64`, with integer `issued_at` and `expires_at` timestamps. Its lifetime must not exceed 15 minutes. Request a fresh attestation for each ephemeral runner. Never paste a placeholder or create a self-signed attestation unless that signer is the separately established trust root.

Then run:

```bash
./tools/bootstrap_brain_cloud_executor.sh
```

The bootstrap refuses to register unless x86_64, /dev/kvm, QEMU, OVMF tooling and
the cryptographic Cloud Executor Gate all pass. It registers an ephemeral, one-job
GitHub runner with the complete Brain Cloud labels. If the attestation expires while
the runner waits in queue, the gate fails closed and a fresh runner/attestation is required.

## Critical boundary

The workflow never sets Cloud Executor identity. The host does.

Registration alone is not success. The executor must pass:

1. Cloud Executor Gate.
2. Brain Authority contract.
3. Windows Server 2025 real boot.
4. Independent Windows completion gate.
5. Evidence preservation.

Only then may the system emit `BRAIN_WINDOWS_REAL_BOOT_CLOSED_LOOP=VERIFIED`.
