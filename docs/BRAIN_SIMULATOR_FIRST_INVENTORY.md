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


## Supplemental read-only audit (continuation)

Additional files fetched from `main`:

| Component | Path | What source establishes | Limitation |
|---|---|---|---|
| Device/cloud federation | `brain_v12/brain/device_cloud_federation.py` | Planning policy for device roles/offload; states it does not connect to devices or provision resources. | A plan is not execution evidence. |
| Virtual Arkan provisioner | `brain_v12/virtual_hardware/arkan_provisioner.py` | Explicitly simulation-first; persists logical identity/configuration and does not start a hypervisor or native guest OS. | Logical capacity is not physical capacity. |
| Virtual hardware API | `brain_v12/virtual_hardware/api.py` | API for the virtual-computer profile and persisted checkpoints. | Route presence does not prove a running guest. |
| Device federation docs | `docs/BRAIN_DEVICE_CLOUD_FEDERATION.md` | Documents a software-defined Arkan indicator and explicitly labels it simulated; physical identity/execution eligibility are not established by a shared heartbeat alone. | Must preserve `identity_verified=false` and execution-ineligible states until independent evidence exists. |
| Simulation-first remote fabric | `docs/SIMULATION_FIRST_REMOTE_FABRIC.md` | Describes virtual mode as the default for remote-device workflows and a separate explicit real probe. | Wiring and runtime behavior still need tests. |
| Self-healing verification gate | `brain_v12/self_healing/verification_gate.py` | Runs named verification commands and writes a verification evidence file. | Audit must verify freshness, task association, and that callers reject stale evidence. |
| Repair dispatcher | `brain_v12/self_healing/repair.py` | Evidence-driven repair dispatcher with candidate verification and rollback-related behavior. | Must be tested for bounded attempts and rejection on failed mandatory checks. |
| Review loop | `brain_v12/self_healing/review_loop.py` | Documents a bounded review/run/verify/repair loop; does not accept a generated patch as success without verification. | Security review and main-branch protection need separate verification. |
| Continuous evolution | `brain_v12/self_healing/continuous_evolution.py` | Supports bounded or persistent cycles, with review and post-repair verification. | Persistent mode needs explicit operational bounds and failure-loop controls. |
| Future evolution | `brain_v12/self_healing/future_evolution.py` | Produces evidence-backed proposed evolution plans; says predictions are not success. | Recommendations must not bypass authorization or verification. |
| Movie Summary Factory | `brain_v12/movie_summary_factory/engine.py` | Defines deterministic production stages and job structure. | A job plan is not a completed media artifact. |
| Cinematic V3 | `brain_v12/movie_summary_factory/cinematic_v3.py` | Provides cinematic planning/quality logic. | A quality plan is not proof of cinematic QC passing. |
| Simulator CI workflow | `.github/workflows/brain-error-recovery.yml` | Includes simulator API and related tests on relevant changes. | It is not the real Windows boot workflow. |
| Arkan virtual-computer docs | `docs/ARKAN_VIRTUAL_COMPUTER.md` | Explicitly says simulator tests do not establish native guest OS boot. | Keep real-boot evidence gate independent. |

### Current CI evidence observed during this audit

For the inventory branch head commit `1b4c198aca3e221c180c8c1860ef24f797808d53`, the workflow lookup returned:
- `Brain Fabric Tests`: `in_progress`
- `Brain Cloud Mining Control Plane`: `in_progress`
- `Brain Reflection E2E`: `success`
- `Brain Reasoning Loop`: `success`

These are workflow observations at audit time, not a complete required-check determination. The combined commit-status endpoint returned no status entries; that does not mean all required checks passed. The inventory change itself is documentation-only and runtime tests were not run locally.

### Updated migration order

1. **Keep simulation-first Arkan semantics explicit.** Reuse the existing virtual-computer profile instead of adding a duplicate simulator without evidence it is needed.
2. **Audit the simulator registry against actual route/backend consumers.** Map catalog entries to real files, test adapters, and runtime status fields before editing selectors.
3. **Audit evidence freshness and task binding.** Trace verification-gate output into completion/boot gates; stale or unbound evidence must be rejected.
4. **Preserve the independent real Windows boot lane.** The real-boot workflow and execution-contract issuer remain untouched by simulation routing.
5. **Audit self-healing and media after the common evidence contract is mapped.** These systems already have verification/planning components; prefer focused tests and adapters over broad rewrites.

**Continuation result:** broader source coverage added to this document, but the repository-wide search is still partial. No runtime code changed, no executor was invoked, and no real OS boot is claimed.
