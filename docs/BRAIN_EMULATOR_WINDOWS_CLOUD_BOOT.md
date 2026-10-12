# ChatGPT/Brain Emulator — Windows Server 2025 Cloud Boot Readiness

## Decision from source inspection

The existing PowerShell emulator is a deterministic sandbox, not a Windows operating system or shell. Its responses explicitly use `reality: SIMULATED`. It cannot create or boot Windows Server 2025 by itself.

The repository does contain a separate real execution route:
- `brain_v12/brain/execution_gateway.py` — Brain-owned authorization gateway.
- `brain_v12/brain/windows_real_boot_qemu_adapter.py` — QEMU/KVM real-boot adapter; requires a verified contract and host assets.
- `brain_v12/brain/windows_cloud_executor.py` — provider-neutral VM lifecycle and guest heartbeat verification.
- `brain_v12/brain/windows_cloud_provider_factory.py` — explicit Terraform/OpenNebula provider selection; no default provider.
- `brain_v12/brain/terraform_windows_cloud_provider.py` — Terraform plan/review/apply flow; reviewed plan and explicit apply enablement are required.
- `brain_v12/brain/opennebula_windows_cloud_provider.py` — OpenNebula flow; a real template and explicit apply enablement are required.
- `brain_v12/brain/windows_cloud_task_executor.py` — submits tasks only after a fresh, verified Windows guest heartbeat.
- `.github/workflows/brain-windows-real-boot.yml` — manual workflow for contract-gated QEMU/KVM boot.
- `tools/bootstrap_brain_cloud_executor.sh` — guarded bootstrap for a dedicated Linux x86_64 executor; expects host prerequisites and trusted enrollment inputs.
- `docs/WINDOWS_SERVER_2025_REAL_BOOT_RUNBOOK.md` and `brain_v12/CLOUD_EXECUTOR_ACTIVATION.md` — operational security and acceptance requirements.

## What this change adds

1. `tools/brain_emulator_project_audit.py`: read-only repository/host inventory, required path checks, boot tool checks, KVM/OVMF checks, and a machine-readable blocker report.
2. `tools/install_windows_boot_prerequisites.sh`: opt-in Ubuntu/Debian package installer for QEMU, QEMU utilities, OVMF, xorriso, wimtools, dosfstools, mtools, Python, Git, and diagnostics. It defaults to refusing installation and never configures secrets or creates cloud resources.
3. Two new fixed allowlisted tasks in `brain_v12/tools/brain_emulator_agent.py`:
   - `brain_project_audit`
   - `windows_cloud_boot_preflight`

These tasks run the audit script only. They do not run arbitrary shell commands, install packages, provision infrastructure, mint attestations, or bypass contract/approval gates.

## Project purpose and inventory scope

The audit reflects the source-of-truth principles in `PROJECT_MASTER_SPEC.md` and `PROJECT_ROADMAP.md`:
- Brain Core/orchestration, memory, decision/task engines, supervisor, self-healing and verification.
- Cloud execution, device bridge/Termux emulator, runner and evidence flows.
- Cinematic/media factory and media quality gates.
- Quran/knowledge reasoning layer.
- Economic ledger, opportunity, customer/revenue/profit evidence systems.
- Security, recovery, APIs, web UI, workflows, documentation and tests.

The audit counts files in key project areas and checks core Windows boot files. It does not claim that a directory, test file, workflow, or API is operational merely because it exists.

## Run the audit

From the repository root on the host being audited:

```bash
python3 tools/brain_emulator_project_audit.py
python3 tools/brain_emulator_project_audit.py --json --output /tmp/brain-project-audit.json
```

The audit exits with code 0 only when its local boot checks are clear; otherwise it exits 2 and reports blockers. The report contains environment-variable presence only, never values. Local checks cannot validate remote Control Plane settings.

## Install host prerequisites (explicit opt-in)

Review the installer first. Then, on an authorized Ubuntu/Debian Linux x86_64 cloud host:

```bash
BRAIN_ALLOW_SYSTEM_PACKAGE_INSTALL=1 bash tools/install_windows_boot_prerequisites.sh
```

Run it as an unprivileged operator with sudo. It changes OS packages only. It does not create a VM. Package availability does not imply KVM is exposed by the cloud provider; `/dev/kvm` must be readable and writable by the executor account.

Do not run the package installer on the Android emulator as a substitute for a Linux x86_64 cloud executor. The Android device can report its own capabilities, but it is not the production KVM host.

## How the emulator receives the audit

The device agent only accepts fixed task names. Queue one of the two tasks through the existing authenticated Brain device-task mechanism; the agent runs the audit and reports a compact result. The exact task name is the payload's `task` field, either `brain_project_audit` or `windows_cloud_boot_preflight`. The current change does not add a new unauthenticated HTTP endpoint or arbitrary command execution.

## Real cloud boot prerequisites

Before a real boot can start, verify all of the following using trusted sources:
1. A real cloud provider or authorized Brain-owned Linux x86_64 host is selected. If using QEMU, it must expose usable KVM; if using Terraform/OpenNebula, provider CLI/configuration and an owner-reviewed plan/template must exist.
2. QEMU/QEMU-img, xorriso, wimlib-imagex, mkfs.vfat, mcopy, OVMF, and a writable workspace exist on the executor host.
3. The runner is dedicated, correctly labelled, isolated from operator credentials, and has passed the Cloud Executor Gate.
4. The Control Plane has the trusted enrollment digest, hostname/architecture binding, signing key, durable replay/nonce store, and valid owner-authorized approval/lease/checkpoint state. These are remote settings and must not be copied into the repo or printed in logs.
5. The protected `windows-real-boot` GitHub Environment contains all six secrets named in the runbook; presence must be checked without exposing values.
6. The workflow receives a fresh, signed, single-use executor attestation and a short-lived signed Windows execution contract. The real contract must not be fabricated or bypassed.
7. Use a legitimate Windows Server 2025 x64 installation media source and respect licensing/registration requirements.

## Success definition

A green preflight, a queued workflow, an ISO download, a running QEMU process, or an infrastructure VM state is not sufficient. Acceptance requires all evidence from the same run:
- guest-generated `windows-boot-evidence.json`;
- `WINDOWS_BOOT_VERIFIED` marker copied from the guest evidence volume;
- independent completion gate passing;
- retained workflow artifacts that establish the evidence chain.

Only after that should the Brain report `BRAIN_WINDOWS_REAL_BOOT_CLOSED_LOOP=VERIFIED`.

## Current known limitation

This PR adds the audit and safe preparation tooling, not cloud credentials, a provider account, KVM capability, owner approval, or a signed execution contract. It does not dispatch a real boot. Once the branch is reviewed and merged, run the audit on the actual cloud executor host and fix the reported blockers. Never interpret a successful audit run on Android or on a host without KVM as proof that a cloud Windows guest booted.
