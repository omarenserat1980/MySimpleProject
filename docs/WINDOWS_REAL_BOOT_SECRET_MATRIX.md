# Windows Real-Boot Secret and Host Matrix

This matrix is checked against `.github/workflows/brain-windows-real-boot.yml` on main.

## Required GitHub Environment secrets

Create all six as secrets in the protected `windows-real-boot` Environment. The workflow preflight blocks if any is empty.

1. `BRAIN_CLOUD_EXECUTOR_REGISTRY_URL_PROTECTED` — HTTPS registry base URL.
2. `BRAIN_CLOUD_EXECUTOR_TOKEN_PROTECTED` — authorized executor registry credential.
3. `BRAIN_CLOUD_EXECUTOR_ATTESTATION_PUBLIC_KEY_B64_PROTECTED` — trusted Ed25519 attestation issuer public key.
4. `BRAIN_AUTHORITY_PUBLIC_KEY_B64_PROTECTED` — authority public key for signed execution-contract verification.
5. `BRAIN_WINDOWS_CONTROL_PLANE_URL_PROTECTED` — HTTPS Brain Control Plane base URL.
6. `BRAIN_WINDOWS_CONTRACT_DELIVERY_KEY_PROTECTED` — high-entropy delivery key shared with the Control Plane.

Do not create repository-level copies or placeholders. The workflow maps these Environment secrets into job variables; host environment variables cannot override job-level values with the same name.

## Trusted host configuration (not YAML, not Compose)

Provision these on the authorized Brain-owned runner host/service:

- `BRAIN_INTERNAL_RUNNER_FLAG=1`
- `BRAIN_CLOUD_EXECUTOR=1`
- `BRAIN_CLOUD_EXECUTOR_ID` — stable enrolled executor ID.
- `BRAIN_CLOUD_EXECUTOR_ATTESTATION_FILE` — writable path for the fresh single-use attestation document.

Do not set trusted identity flags in Docker images, Compose, or workflow YAML. Do not place private signing keys, raw owner approvals, or enrollment credentials in the repository.

## Required real-boot proof

Before dispatch, independently verify that the HTTPS Control Plane is deployed and configured, the executor is enrolled, and the dedicated Linux x64 runner has QEMU/OVMF and usable `/dev/kvm`. A successful CI/security workflow is not proof of these external prerequisites.

Acceptance requires guest-generated `windows-boot-evidence.json`, `WINDOWS_BOOT_VERIFIED`, `BRAIN_WINDOWS_REAL_BOOT_CLOSED_LOOP=VERIFIED`, an independent completion-gate pass, and artifacts from the same workflow run.
