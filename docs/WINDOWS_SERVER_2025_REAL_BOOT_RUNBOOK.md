# Windows Server 2025 Real-Boot Operator Runbook

## Current acceptance rule

Do not report success because a workflow was queued, a gate passed, an ISO was created, or QEMU started. Acceptance requires the guest-generated `windows-boot-evidence.json`, the `WINDOWS_BOOT_VERIFIED` marker copied from the guest evidence volume, a passing independent completion gate, and the uploaded run artifacts from the same workflow run.

The real-boot workflow is intentionally manual (`workflow_dispatch`). A push-triggered run with zero jobs is not a boot attempt.

## Before dispatch

### 1. Prepare the Brain Control Plane (not the runner)

Configure the Control Plane with the real, owner-authorized identity, checkpoint, current leadership lease, unexpired owner approval, human approval token, authority private signing key, and approval verification configuration expected by the existing issuer. Keep owner/human approval material and the authority private key on the Control Plane only.

The issuer fails closed when required identity/checkpoint/lease/approval material is missing or expired. Do not create placeholder approvals or fake leases to make a gate pass.

The Control Plane must expose the Brain API over HTTPS, reachable from the dedicated self-hosted runner. Confirm the deployed code includes `POST /api/brain/windows/contracts/issue`.

### 2. Configure GitHub Actions secrets

In repository Settings → Secrets and variables → Actions, add these repository or appropriately scoped environment secrets:

- `BRAIN_WINDOWS_CONTROL_PLANE_URL`: base URL of the real HTTPS Control Plane (no credentials embedded in the URL).
- `BRAIN_WINDOWS_CONTRACT_DELIVERY_KEY`: high-entropy delivery key shared by the Control Plane endpoint and GitHub Actions.
- `BRAIN_AUTHORITY_PUBLIC_KEY_B64`: authority public key used by the runner-side contract gate to verify the signed contract.

Never put the authority private key, owner approval signing key, human approval token, or raw owner approval in GitHub secrets. The runner receives only the short-lived signed contract and public verification key. Rotate the delivery key if it may have been exposed.

### 3. Verify the runner

The selected runner must be the authorized Brain-owned Linux x64 self-hosted runner with all required labels:

`brain-internal`, `qemu`, `windows-real-boot`, `brain-cloud-executor`

It must already have `qemu-system-x86_64`, `qemu-img`, `xorriso`, `wimlib-imagex`, `mkfs.vfat`, `mcopy`, OVMF firmware, and readable/writable `/dev/kvm`. This workflow does not install host packages automatically.

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
