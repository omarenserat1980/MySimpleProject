# Windows Server 2025 Real-Boot Operator Runbook

## Current acceptance rule

Do not report success because a workflow was queued, a gate passed, an ISO was created, or QEMU started. Acceptance requires the guest-generated `windows-boot-evidence.json`, the `WINDOWS_BOOT_VERIFIED` marker copied from the guest evidence volume, a passing independent completion gate, and the uploaded run artifacts from the same workflow run.

The real-boot workflow is intentionally manual (`workflow_dispatch`). A push-triggered run with zero jobs is not a boot attempt.

## Before dispatch

### 1. Prepare the Brain Control Plane (not the runner)

Configure the Control Plane with the real, owner-authorized identity, checkpoint, current leadership lease, unexpired owner approval, human approval token, authority private signing key, and approval verification configuration expected by the existing issuer. Keep owner/human approval material and the authority private key on the Control Plane only.

The issuer fails closed when required identity/checkpoint/lease/approval material is missing or expired. Do not create placeholder approvals or fake leases to make a gate pass.

The Control Plane must expose the Brain API over HTTPS, reachable from the dedicated self-hosted runner. Confirm the deployed code includes `POST /api/brain/windows/contracts/issue`.

### 2. Configure the protected GitHub Actions Environment

In repository Settings → Environments, create `windows-real-boot` and configure **Required reviewers** so the repository owner must approve the deployment. Save and verify the protection rules before any manual dispatch. A workflow's `environment:` reference does not itself enable reviewer protection. Restrict deployment branches to the reviewed boot workflow branch and/or `main`, according to the repository's release policy.

Create these **environment secrets only** in `windows-real-boot`:

- `BRAIN_WINDOWS_CONTROL_PLANE_URL_PROTECTED`: base URL of the real HTTPS Control Plane (no credentials embedded in the URL).
- `BRAIN_WINDOWS_CONTRACT_DELIVERY_KEY_PROTECTED`: high-entropy delivery key shared by the Control Plane endpoint and GitHub Actions.
- `BRAIN_AUTHORITY_PUBLIC_KEY_B64_PROTECTED`: authority public key used by the runner-side contract gate to verify the signed contract.

Do not create repository-level copies of these protected secret names. Remove any old repository-level `BRAIN_WINDOWS_CONTROL_PLANE_URL`, `BRAIN_WINDOWS_CONTRACT_DELIVERY_KEY`, or `BRAIN_AUTHORITY_PUBLIC_KEY_B64` secrets if they were configured for this workflow; the workflow must not fall back to unprotected repository secrets.

Never put the authority private key, owner approval signing key, human approval token, or raw owner approval in GitHub secrets. The runner receives only the short-lived signed contract and public verification key. Rotate the delivery key if it may have been exposed.

### 3. Verify the runner

The selected runner must be the authorized Brain-owned Linux x64 self-hosted runner with all required labels:

`brain-internal`, `qemu`, `windows-real-boot`, `brain-cloud-executor`

It must already have `qemu-system-x86_64`, `qemu-img`, `xorriso`, `wimlib-imagex`, `mkfs.vfat`, `mcopy`, OVMF firmware, and readable/writable `/dev/kvm`. This workflow does not install host packages automatically.


### 4. Provision the signed cloud-executor attestation (host-side)

The cloud-executor gate requires more than runner labels and installed binaries. Before the runner is eligible, provision these variables through the trusted runner service/host configuration, never in workflow YAML and never by a job step:

- `BRAIN_CLOUD_EXECUTOR=1`
- `BRAIN_CLOUD_EXECUTOR_ID`: stable ID for this authorized executor
- `BRAIN_CLOUD_EXECUTOR_ATTESTATION_FILE`: path to a fresh signed attestation document on the host
- `BRAIN_CLOUD_EXECUTOR_ATTESTATION_PUBLIC_KEY_B64`: out-of-band trusted Ed25519 issuer public key
- `BRAIN_CLOUD_EXECUTOR_REGISTRY_URL`: HTTPS base URL for the central Brain executor registry
- `BRAIN_CLOUD_EXECUTOR_TOKEN`: host-provisioned registry credential

The attestation must use schema `brain.cloud-executor-attestation.v2`, match the current hostname and `x86_64` architecture, target audience `brain-cloud-executor`, have a valid issuer signature, and expire within the verifier's five-minute maximum validity window. The central registry must atomically consume the attestation nonce at `POST /api/cloud-executor/attestation/consume`; repeated nonces must be rejected. The gate also actually starts QEMU with `-accel kvm` to probe KVM initialization.

Do not mint a production signing key in CI, fabricate an attestation, echo tokens, or bypass the registry. If these host-side values or the trusted registry are unavailable, the gate must fail closed and real boot must remain blocked. Verify only the presence and successful gate result; do not publish secret values in logs or artifacts.

## Manual dispatch

1. Open Actions → **Brain Windows Real Boot Evidence**.
2. Select **Run workflow** on the intended PR branch only after reviewing its code and the Control Plane configuration.
3. Supply a direct, legitimate Microsoft Windows Server 2025 x64 ISO URL available to the operator. Microsoft registration/licensing requirements still apply.
4. Set the timeout within the workflow's configured limits and start the run.
5. Follow the same run through contract delivery, contract verification, ISO inspection, fresh QCOW2 creation, KVM boot, guest evidence, and independent completion gate.

The workflow creates a fresh `windows-server-2025.qcow2` and a separate evidence image in the runner workspace. Do not point it at or overwrite an existing VM disk.

## Stop conditions and diagnosis

- `BRAIN_WINDOWS_CONTROL_PLANE_URL` or delivery key missing: configure the corresponding GitHub Actions secret; do not bypass contract delivery.
- HTTPS, HTTP authentication, binding, signature, or expiry failure: repair the real Control Plane/contract configuration; do not disable verification.
- No eligible runner or missing tools/`/dev/kvm`: repair runner registration/capabilities before retrying.
- ISO/image inspection failure: verify the URL returned the expected Microsoft media and inspect the run artifact/log.
- `WINDOWS_BOOT_EVIDENCE_NOT_FOUND`: inspect QEMU console/serial logs and guest setup evidence; a running QEMU process alone is not success.
- Completion gate failure: retain artifacts and diagnose the specific failed invariant before another run.

## Evidence checklist

A successful acceptance record must point to the same workflow run and include:

- verified Control Plane contract gate and contract SHA-256;
- executor gate evidence identifying the same runner;
- ISO and proof-media SHA-256 files;
- QEMU/KVM boot logs and the guest-written evidence file;
- guest boot marker copied from the evidence volume;
- passing `windows-completion-gate.json` and final workflow success.

## Change-control boundary

The related hardening work is tracked in PR #226 and remains subject to owner review. Do not merge it automatically. No Windows Server 2025 boot is claimed until the acceptance evidence above exists.
