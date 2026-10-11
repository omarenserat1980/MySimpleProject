# Windows Server 2025 Real-Boot Operator Runbook

## Purpose and completion rule

This runbook describes the guarded, manual Windows Server 2025 real-boot workflow:
`.github/workflows/brain-windows-real-boot.yml`.

A successful CI test suite is **not** proof that Windows booted. Report success only when the real-boot workflow completes and its final evidence gate reports `WINDOWS_BOOT_VERIFIED` and `BRAIN_WINDOWS_REAL_BOOT_CLOSED_LOOP=VERIFIED`. A blocked or failed preflight means no successful boot has been established.

## 1. Verify protected environment configuration

In GitHub, open **Settings → Environments → windows-real-boot → Environment secrets**. Confirm that each secret exists and is populated without copying its value into an issue, chat, workflow output, or log:

- `BRAIN_CLOUD_EXECUTOR_REGISTRY_URL_PROTECTED`
- `BRAIN_CLOUD_EXECUTOR_TOKEN_PROTECTED`
- `BRAIN_CLOUD_EXECUTOR_ATTESTATION_PUBLIC_KEY_B64_PROTECTED`
- `BRAIN_AUTHORITY_PUBLIC_KEY_B64_PROTECTED`
- `BRAIN_WINDOWS_CONTROL_PLANE_URL_PROTECTED`
- `BRAIN_WINDOWS_CONTRACT_DELIVERY_KEY_PROTECTED`

The workflow checks these names at runtime. A presence check does not prove that credentials are valid or that the remote services are reachable; the subsequent attestation and contract gates must pass too.

## 2. Verify the internal runner host

The workflow requires a self-hosted Linux x64 runner with all labels:

`self-hosted, linux, x64, brain-internal, qemu, windows-real-boot, brain-cloud-executor`

Before dispatch, confirm on the runner host that:

- The runner is online and registered with the expected labels.
- `BRAIN_INTERNAL_RUNNER_FLAG=1` is injected by the runner service/host configuration, not by workflow YAML.
- `qemu-system-x86_64`, `qemu-img`, `xorriso`, `wimlib-imagex`, `mkfs.vfat`, and `mcopy` are installed.
- `/usr/share/OVMF/OVMF_CODE_4M.fd` and `/usr/share/OVMF/OVMF_VARS_4M.fd` exist.
- `/dev/kvm` is a character device and is readable/writable by the runner account; QEMU can initialize KVM.
- The host has sufficient free memory, CPU capacity, and disk space for a 64 GiB virtual disk, installer media, and evidence artifacts.

Do not substitute software emulation and do not add the internal-runner flag to the workflow itself. If any prerequisite is missing, stop and fix the host before dispatch.

## 3. Verify the control plane and execution contract

The workflow obtains a short-lived, single-use signed executor attestation from the configured registry, verifies it in the same job, fetches the execution contract over the configured control-plane path, and runs the closed-loop contract gate. Both gates must report verified. Never paste tokens, delivery keys, private keys, raw attestation payloads, or contract secrets into logs or comments.

## 4. Dispatch the workflow deliberately

Open **Actions → Brain Windows Real Boot Evidence → Run workflow** on the intended branch. Use the registered Microsoft Windows Server 2025 x64 ISO URL or the workflow's default official Microsoft link. Confirm that the `windows-real-boot` environment protection rules and any required approvals are satisfied.

This workflow downloads installation media, creates a virtual disk, and boots an installer on the internal runner. Run it only when the runner is authorized and has enough capacity. Do not trigger it merely to test CI or when prerequisites remain unverified.

## 5. Review the evidence, not just the green badge

Inspect the run log and the artifact named `brain-windows-server-2025-real-boot-evidence-<run_id>`. Confirm:

- Secret preflight passed without secret values being printed.
- Internal runner and QEMU/KVM gates passed.
- Executor attestation and execution contract gates both report verified.
- The guest evidence says `WINDOWS_BOOT_VERIFIED`, identifies Windows Server 2025 and AMD64/x86_64, and records guest boot, network, and storage checks.
- The boot phase confirms the installed virtual disk was booted, not merely the ISO installer.
- The independent `WindowsCompletionGate` returns `WINDOWS_BOOT_VERIFIED`.
- The final workflow step prints `BRAIN_WINDOWS_REAL_BOOT_CLOSED_LOOP=VERIFIED`.

If a run fails or is blocked, preserve its run URL and sanitized failure reason. Do not label the server deployed, booted, or reachable. Fix the specific failed gate, then re-run only after rechecking prerequisites.

## Current verification boundary

This document is an operator checklist, not live evidence of environment-secret values, runner connectivity, deployment, or guest boot. Those facts must be established by the protected environment and a successful real-boot workflow run.
