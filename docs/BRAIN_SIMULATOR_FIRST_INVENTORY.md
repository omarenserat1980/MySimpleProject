# Electronic Brain — Simulator-First Inventory (Phase 1)

**Status:** Initial repository-backed inventory; not a complete repository audit  
**Baseline:** `main` at branch creation time  
**Branch:** `docs/simulator-first-inventory-phase1`  
**Scope:** Documentation only. No runtime code, executor, secret, workflow, VM, or production configuration changed.

## Truth and safety boundaries

- Repository files prove that code or a contract exists; they do not prove that a service is connected or a device is online.
- Registration is not connectivity. Connectivity is not readiness. Readiness is not execution.
- Simulator results cannot prove native Linux startup or Windows Server 2025 boot.
- Keep the real Windows boot workflow, signed execution-contract path, Termux/device bridge, and media publishing executors.
- Do not provision paid cloud resources or perform real external side effects as part of tests.

## Verified source files and current role

| Component | Repository path | Evidence from inspection | Status |
|---|---|---|---|
| Simulator registry/API | `brain_v12/brain/universal_simulator_api.py` | Catalog, discovery candidates, registration logic, connection states, sanitized diagnostics/repair proposals. Source comments explicitly say path discovery does not prove external connectivity. | Inspected |
| Registry documentation | `brain_v12/docs/UNIVERSAL_SIMULATOR_CHATGPT_REPAIR.md` | Documents registry endpoints and the distinction between discovery, registration, and probing. | Inspected |
| Brain Card preflight | `brain_v12/brain/brain_card_preflight.py` | Versioned in-process route contract; its scope is the live in-process route table. | Inspected |
| Preflight specification | `docs/BRAIN_PREFLIGHT_GATE.md` | Defines preflight ordering and notes that the current route snapshot is not proof of remote health or a universal canonical registry. | Inspected |
| ChatGPT Simulator integration prompt | `docs/CHATGPT_SIMULATOR_BRAIN_CARD_INTEGRATION_PROMPT.md` | Defines the intended Brain Card/path-registry role for the simulator and Suggestions Engine. | Inspected |
| Linux/Windows host preflight | `brain_v12/tools/arkan_windows_server_2025_preflight.py` | Checks Linux x86-64, CPU/memory/disk, KVM, QEMU/media tools, UEFI, and a contract-gate flag; output keeps boot NOT_VERIFIED. | Inspected |
| Real Windows boot workflow | `.github/workflows/brain-windows-real-boot.yml` | Protected self-hosted Linux x64 runner, protected secrets, execution/attestation gates. Must remain separate from simulation tests. | Inspected |
| Windows execution contract | `brain_v12/brain/windows_execution_contract_issuer.py` | Uses authority policy, signing, checkpoint identity, leadership lease, and owner-approval helpers. | Inspected |
| Universal simulator tests | `brain_v12/tests/test_universal_simulator_api.py` | Focused tests for simulator API behavior and diagnostic sanitization. | Inspected |
| Termux/device bridge | `brain_v12/brain/device_bridge.py` | Defines an allowlisted device-agent task bridge; connectivity/completion still need runtime evidence. | Inspected |
| Film completion gate | `brain_v12/brain/film_completion_gate.py` | Uses ffprobe and completion checks; does not by itself prove publishing. | Inspected |
| Linux simulator | [PR #519](https://github.com/omarenserat1980/MySimpleProject/pull/519) | PR description reports deterministic simulation and a passing focused simulator workflow; not evidence of native Linux or Windows boot. | PR metadata reviewed; not re-run here |

## Dependency and control-flow map (initial)

```text
Incoming chat / task / repair request
  -> Brain Card preflight
       -> in-process route/service contract
  -> authorization and permission/contract gates
  -> backend selection
       -> SIMULATOR (isolated tests; explicitly labelled)
       -> REAL_EXECUTOR (explicit real mode + identity/authority)
  -> execution result
  -> independent evidence verification
  -> task record / audit trail

Linux simulator ------------------------------> simulated profile/resource result
Real Linux/QEMU host preflight ----------------> host readiness only
Protected Windows real-boot workflow ----------> guest evidence/completion gate
Device bridge ---------------------------------> Termux/Android task adapter
Media engine ----------------------------------> artifact / technical QC / cinematic QC / publish verification
```

This map is conceptual and based on inspected source contracts; it does not claim every edge is wired end-to-end.

## Indicator migration priorities

1. **Simulator/real truth boundary.** Audit backend selectors and status paths around the simulator API, Brain Card, and task execution. `SIMULATED` must never satisfy a real-execution or boot gate.
2. **Linux and QEMU/KVM.** Point resource/profile unit tests at the Linux simulator. Keep host inspection, KVM access, and actual QEMU execution in a separate real-host path.
3. **Windows Server 2025.** Keep simulation fixtures separate from `.github/workflows/brain-windows-real-boot.yml`; require fresh, task-bound guest evidence for `BOOT_VERIFIED`.
4. **Termux, Android, PowerShell, Desktop Commander.** Use explicit fake adapters for tests while retaining real adapters. Never infer connectivity from registration, APK build, or command enqueue.
5. **ChatGPT, GitHub, Brain Card, memory/task/decision/self-healing.** Resolve actual route and executor selectors before changing them; do not assume every ingress uses one canonical registry.
6. **Media, publishing, external integrations, economic ledger.** Use fake providers and synthetic artifacts in tests; preserve authorization and external-side-effect gates.

## Open questions for the full read-only audit

- Enumerate every backend selector, path indicator, registry consumer, status serializer, legacy path, and web UI path.
- Confirm tests and CI workflows for Linux simulator PR #519, Windows boot, device bridge, PowerShell/Desktop Commander, Brain Card, media, and self-healing.
- Trace task IDs and evidence provenance from creation through execution and verification.
- Resolve the registry design: Brain Card currently exposes an in-process route snapshot, while the simulator API maintains a separate registry file.
- Verify legacy virtual-hardware paths. The queried path `brain_v12/brain/virtual_hardware/windows_server_backend.py` returned 404 and must not be assumed to exist there.
- Record open-PR dependencies, conflicts, and fresh CI state before implementation.

## Recovery and change record

- No files were modified on `main`.
- This phase adds only this inventory document on a dedicated branch.
- Runtime tests were NOT_RUN because this is a documentation-only artifact.
- No backup/restore test was performed; no runtime or production state changed.
- Rollback: close/revert the documentation-only PR or delete the branch. No executor, secret, VM, or deployed service is affected.

## Status vocabulary

- `PASS`: the named check actually ran and passed.
- `FAIL`: the named check ran and failed.
- `NOT_RUN`: the check was not executed.
- `BLOCKED`: a prerequisite prevented the check.
- `NOT_VERIFIED`: available evidence does not establish the claim.

**Phase 1 result:** partial inventory documented; full repository-wide indicator and dependency enumeration remains NOT_RUN. No real OS boot or external execution is claimed.
