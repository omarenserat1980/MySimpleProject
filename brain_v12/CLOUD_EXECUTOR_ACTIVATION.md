# Cloud Executor Activation

The production Windows executor is a Brain-owned Linux x86_64 cloud VM. Its hostname and architecture binding must be registered in the trusted Brain Control Plane inventory; the runner may not choose these claims in an API request.

## Control Plane configuration

Configure these values out of band on the Brain Control Plane, not in the repository or GitHub workflow:

- `BRAIN_CLOUD_EXECUTOR_HOST_BINDINGS_JSON`: map each enrolled executor ID to a trusted hostname and `x86_64` architecture, for example `{"brain-cloud-ark-01":{"hostname":"brain-runner-01","architecture":"x86_64"}}`.
- `BRAIN_CLOUD_EXECUTOR_ENROLLMENTS_SHA256_JSON`: per-executor enrollment-token hashes.
- `BRAIN_EXECUTOR_ATTESTATION_SIGNING_KEY_B64`: Ed25519 private key from a protected secret store.
- `BRAIN_CLOUD_EXECUTOR_REGISTRY_DB`: shared authoritative challenge/nonce registry.

The host binding must come from the trusted provisioning inventory. Do not populate it from hostname or architecture claims sent by the executor. The API persists the binding in each 60-second challenge and refuses issuance if the inventory binding changes before signing.

## Activation

On the Linux x86_64 executor host, provide:

- `BRAIN_CLOUD_EXECUTOR=1`
- `BRAIN_CLOUD_EXECUTOR_ID`
- `BRAIN_CLOUD_EXECUTOR_ATTESTATION_FILE`
- `BRAIN_CLOUD_EXECUTOR_ATTESTATION_PUBLIC_KEY_B64`
- `BRAIN_CLOUD_EXECUTOR_REGISTRY_URL` (HTTPS)
- `BRAIN_CLOUD_EXECUTOR_TOKEN` (per-executor enrollment token)

Install the public trust key through the independent host-management channel, then run:

```bash
./tools/bootstrap_brain_cloud_executor.sh
```

The issuer signs schema `brain.cloud-executor-attestation.v2`, including the trusted hostname, `x86_64` architecture, executor ID, audience, timestamps, and nonce. The executor checks the signed host binding against its actual local hostname and architecture, then consumes the nonce through the central HTTPS registry. Missing configuration, host mismatch, replay, expiry, or registry failure blocks runner registration.

The bootstrap requires x86_64, usable `/dev/kvm`, QEMU, OVMF tooling, and the Cloud Executor Gate. It registers an ephemeral one-job GitHub runner and starts it in the foreground; it does not install a persistent runner service.

## Critical boundary

The workflow never sets Cloud Executor identity. The host does. Repository changes do not prove that the Control Plane inventory, signing key, or host trust anchor has been configured on a real machine.

Registration alone is not success. The executor must pass:

1. Cloud Executor Gate.
2. Brain Authority contract.
3. Windows Server 2025 real boot.
4. Independent Windows completion gate.
5. Evidence preservation.

Only then may the system emit `BRAIN_WINDOWS_REAL_BOOT_CLOSED_LOOP=VERIFIED`.
