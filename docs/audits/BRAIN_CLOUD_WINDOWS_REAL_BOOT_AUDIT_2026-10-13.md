# Brain Cloud / Windows Real Boot Audit — 2026-10-13

## Scope and evidence boundary

Repository: `omarenserat1980/MySimpleProject`  
Reference commit requested: `8cec9b8b9ca0f1bbb26c424ea0e0aa9a3fe0b80a`  
Workflow run inspected: [38388463018](https://github.com/omarenserat1980/MySimpleProject/actions/runs/38388463018)  
Workflow job inspected: [115265980498](https://github.com/omarenserat1980/MySimpleProject/actions/runs/38388463018/job/115265980498)  
Run head SHA: `bd651ef3862168bd1b60d5e859f81a3384306b25`  
Audit timestamp: 2026-10-13 UTC.

This is an evidence report, not a claim that production was repaired. No production secrets were read or changed, no paid infrastructure was created, and no cloud provisioning/apply was performed.

## Current verdict

**NO-GO for Windows real-boot completion.** The inspected run proves that a Microsoft Windows Server 2025 Evaluation ISO was downloaded and its bytes matched the workflow-provided trusted SHA-256, and that QEMU launched the installer under software emulation. Its own evidence explicitly says `windows_guest_boot_verified: false`. It does not prove completed installation, boot from the installed disk, guest-agent authentication, heartbeat, or a real task.

**Cloud Executor: PARTIAL / runtime verification pending.** The repository has Ed25519-based attestation code, host-binding checks, short-lived challenges, nonce consumption, and focused unit tests. The inspected production log query did not return matching challenge-path entries, so current HTTP behavior and the full production cycle remain unverified. Do not infer that an old 403 is still happening, or that the current path works, without a fresh request and trace.

**Render: PARTIAL / deployment observed, readiness not independently proven.** Render reported a successful deploy for the Brain Control Plane on 2026-10-13. Deployment success alone is not an application readiness or authentication proof. The audit did not retrieve a trustworthy current readiness response or a fresh authenticated attestation transaction.

## Confirmed findings

### 1. Software-node workflow is not the real-boot workflow

Run `38388463018` ran job `provision-software-node` and uploaded artifact `brain-software-executor-evidence` (artifact ID `11808815836`, SHA-256 digest `589eefd4fed6445ffc49eda946f9d007fbee50c53d1ef23f515b886ce399d6a5`). The job completed successfully, but its log records:

- `accelerator: tcg`
- `windows_boot_verified: false`
- QEMU was started with `-machine q35,accel=tcg` and the original installer ISO.
- The produced evidence states that the display capture does not prove completed Windows installation.

Therefore this run must not be accepted as the end-to-end Windows real-boot result.

### 2. KVM was present but unusable in that runner

The job log reports `/dev/kvm` exists but is neither readable nor writable for the job. The software-node probe consequently selected TCG. This is a concrete runner capability/permission limitation for that run, not proof of a Windows guest failure.

The separate real-boot workflow contains a fail-closed check requiring `/dev/kvm` to be a readable and writable character device. That gate must remain strict; do not downgrade it to TCG or bypass it to obtain a green result.

### 3. Existing attestation safeguards and tests

Inspected files:

- `brain_v12/brain/cloud_executor_attestation_issuer.py`
- `brain_v12/brain/cloud_executor_attestation_api.py`
- `tools/request_cloud_executor_attestation.py`
- `brain_v12/tests/test_cloud_executor_attestation_api.py`
- `.github/workflows/brain-windows-real-boot.yml`
- `brain_v12/windows_setupcomplete.cmd`

The inspected API test file covers a successful challenge → issue → consume flow, inventory host binding, rejection of caller-supplied host overrides, missing host binding, invalid token, unregistered executor, replay rejection, and missing signing key. These are code-level tests; they were not run as part of this audit.

The issuer requires TLS for PostgreSQL registry URLs and uses Ed25519 signing. Production correctness still depends on actual protected configuration, registry persistence, executor authentication, and a fresh end-to-end transaction.

### 4. ISO checksum policy

The inspected workflow rejects a missing/non-hex trusted SHA-256 and stops when downloaded bytes do not match it. The successful run logged `MICROSOFT_ISO_SHA256_VERIFIED=PASS`. This verifies the comparison performed by that run; the durable artifact and workflow inputs should still be checked to establish which independently trusted Microsoft checksum was supplied. A locally calculated digest by itself is not provenance.

## Root cause / hypotheses ledger

| Area | Evidence-backed conclusion | Remaining verification |
|---|---|---|
| Windows real boot | The inspected successful job was installer-only and explicitly marked guest boot unverified. | Run the dedicated `brain-windows-real-boot.yml` job on a Linux x86_64 executor with usable KVM and approved environment secrets. |
| KVM | `/dev/kvm` existed but was not readable/writable; software-node selected TCG. | Confirm permissions/capabilities on the actual protected real-boot runner before starting. |
| Cloud Executor | Attestation code and focused tests exist. No fresh production challenge/issue/consume HTTP evidence was obtained. | Test no-auth, invalid token, unregistered executor, host/architecture mismatch, invalid/expired/replayed challenge, and valid single-use cycle; record HTTP status and trace ID only. |
| Render | A deploy succeeded. No verified current readiness/attestation response was obtained in this audit. | Probe readiness and authenticated attestation endpoints safely; do not expose tokens, signatures, or request headers. |
| Guest agent / heartbeat / task | No artifact from this run proves these conditions. | Require guest-origin evidence linked to the same run, executor, VM identity, and timestamps. |

## Required safe next steps

1. Read the current protected Environment configuration through authorized secret-presence checks only; never print values. Confirm executor enrollment digest entries and host bindings preserve all valid entries.
2. Verify the registered executor identity, host, architecture, and trusted package fingerprint against an independent enrollment source.
3. Run the Cloud Executor test suite in CI and execute a fresh protected challenge → Ed25519 issue → consume transaction. Record actual HTTP statuses, allowlisted logical error codes, and correlation IDs without credentials.
4. Verify that the dedicated real-boot runner is Linux x86_64 and that `/dev/kvm` is a readable/writable character device. Stop if this gate fails.
5. Require the dedicated workflow to install to its virtual system disk, reboot without the installer as the boot source, and collect evidence written by the guest itself.
6. Require authenticated guest-agent heartbeat and an authorized task result linked to the same run before the completion gate can pass.
7. Run the dedicated completion gate and publish all evidence even on failure. Any missing, stale, host-generated, cross-run, or inconsistent evidence must produce NO-GO.
8. Update the existing project specifications, roadmap, decisions, changelog, and README only alongside verified code/test changes. Preserve legacy requirements.

## Safety and recovery

- No Render environment variables were modified.
- No GitHub secrets were read or changed.
- No paid cloud resources were created and no infrastructure apply was run.
- No workflow was dispatched or rerun by this audit.
- The artifact from run `38388463018` expires on 2026-10-20; preserve it through the authorized GitHub artifact workflow if it is needed for later forensic review.
- Before any future production change, capture the current deployment/configuration state and prepare a revert commit. Never weaken authentication, trusted ISO hash validation, KVM requirements, or completion-gate conditions to force success.

## Test execution status

- Cloud Executor unit tests: **not run during this audit**.
- Full repository suite: **not run during this audit**.
- Production challenge/signature/consume cycle: **not run during this audit**.
- Windows installation and installed-disk reboot: **not proven by inspected run**.
- Guest-agent authentication, heartbeat, and task execution: **not proven**.

Final status: **PARTIAL audit; NO-GO for end-to-end completion**.
