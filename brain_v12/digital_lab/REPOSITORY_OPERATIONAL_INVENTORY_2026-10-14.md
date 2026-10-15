# Electronic Brain — Repository Operational Inventory

- **Inventory date:** 2026-10-14
- **Repository:** `omarenserat1980/MySimpleProject`
- **Branch inspected:** `main`
- **Inspected commit:** `2ad98ff9a060d738215c5334f99502148121ea8f`
- **Method:** GitHub recursive Git tree metadata, GitHub Actions run metadata, selected source/document reads.
- **Scope:** Repository-source inventory and CI evidence review. This is not a full device, host, or production runtime scan.

## Executive result

The repository tree is readable and contains a large multi-generation codebase. The audit distinguishes source files, candidate test files, successful CI runs, and independently proven live components. These quantities are not interchangeable.

| Measure | Observed value | Interpretation |
|---|---:|---|
| Git tree entries | 2,724 | Recursive tree response; not truncated |
| Files (blobs) | 2,562 | Exact file entries in inspected tree |
| Python files | 1,756 | Source and test Python files combined |
| Python files under `brain_v12/` | 1,156 | Source/test Python files combined |
| Candidate test files | 699 | Filename-pattern count only; not a count of test cases or passing tests |
| GitHub Actions workflow YAML files | 171 | Configured workflow files, not active workers/nodes |
| Software hardware-catalog nodes | 354 | Static catalog only: 319 family/component nodes across 18 device families plus 35 logical network-device kinds; not live machines or running workers |
| Physical/Termux workers exposed by `WorkerRegistry` | 0 | The current registry explicitly disables device adapters and returns an empty device-worker list |
| Current-main-SHA workflow runs in recent 100-run window | 21 | 20 success, 1 cancelled, 0 failed in this returned window |
| Independently verified live software/device nodes in this audit | 0 | No fresh per-node heartbeat or runtime attestation was collected; this does **not** mean zero nodes exist |
| Components with current, commit-bound runtime evidence manifest | 0 found in tracked paths | The validator and manifest documentation exist, but no populated runtime evidence JSON was found in the tracked tree scan |

## CI evidence

The latest observed scheduled workflow, [Brain Autonomous Cloud Cycle run 38560846678](https://github.com/omarenserat1980/MySimpleProject/actions/runs/38560846678), completed successfully on the inspected main commit. Its job compiled `cloud` and `brain_v12`, ran a targeted test set, classified launch readiness, and uploaded `brain-autonomous-cloud-cycle-evidence`. It explicitly keeps external side effects permission-gated.

The recent Actions API page returned 100 runs across multiple commits: 92 success, 4 cancelled, and 4 failure. This is a mixed-commit history and must not be reported as the current branch's pass rate. For the inspected main SHA, 20 of 21 returned runs succeeded and one was cancelled.

The tracked `verification/latest.json` is a stored snapshot, not a fresh test run tied to this inventory commit. It records successful compile checks and earlier test output (14 speed tests, 4 cinema tests, and a Brain V12 test run reporting 53 tests). These historical counts are not used as proof of a current full-suite pass.

## Additional code-level finding: catalog nodes versus execution nodes

The existing `brain_v12/virtual_hardware/software_hardware_nodes.py` catalog is complete against its own declared families: source inspection counted 18 device families and 319 family/component pairs, plus 35 logical network-device kinds, for **354 catalog entries**. Its own tests assert catalog coverage. These are logical software inventory entries; they do not mean 354 independent processes, full device emulators, physical devices, or live workers.

The current `brain_v12/brain/worker_registry.py` explicitly forces `include_device_adapters=False`, sets `device_bridge=None`, rejects `termux`, `android`, `physical`, and `hardware` worker kinds, and returns empty `device_workers` / `_device_records`. This is a concrete integration boundary preventing Termux/physical agents from appearing in that worker registry. It may be an intentional software-only safety boundary, so it must not be bypassed blindly. The next implementation should keep simulated software workers separate from externally authenticated device agents and require per-agent authentication, capability allowlists, expiring heartbeats, and evidence before any real device is counted as live.

## Missing proof and blockers

1. **Fresh runtime inventory:** Collect a commit-bound `brain_v12/digital_lab/runtime-evidence.json` with one record per required component. Each record must point to a real check, run, or device observation. Missing observations remain `NOT_RUN` or `BLOCKED`.
2. **Node heartbeat / execution probe:** Run an authorized, bounded probe for each registered Termux, Windows, and cloud executor. Record agent ID, observed timestamp, revision, health, capability, and evidence reference. A workflow's success is not a node heartbeat.
3. **Runner API permission:** The existing `WORK_INVENTORY.md` records a runner-watch API permission failure (HTTP 403 / `API_PERMISSION_DENIED`). An owner must verify least-privilege token scope and run a manual execution probe; do not expose secret values.
4. **Windows Server 2025 boot:** The existing work inventory records `WINDOWS_EXECUTION_CONTRACT_FILE_REQUIRED`. A real pre-issued authorized contract and guest-generated boot evidence are required. Do not bypass the contract or claim the VM is running without evidence.
5. **Bitcoin mining:** Source and CI checks for mining intelligence / proof-of-work reference code exist. They do not prove real pool connectivity, accepted shares, sustained hashrate, ASIC hardware, or revenue. Those require separate live pool and payout evidence.
6. **ASIC fabrication:** RTL and digital flow assets are present. They do not prove foundry acceptance, physical silicon fabrication, or a tested manufactured chip.

## Next execution order

1. Generate the populated asset inventory from the exact inspected commit, classifying each record as source-only, test-verified, CI-verified, live-attested, blocked, or not run.
2. Run focused tests for the software-node registry/agent, runtime evidence validator, runtime launcher, ASIC RTL/toolchain, and Bitcoin proof-of-work components on an available hosted runner.
3. Produce a fresh runtime-evidence manifest with evidence references and exact revision; validate it using `brain_v12.digital_lab.runtime_evidence`.
4. Resolve runner authorization and collect node execution probes; separately resolve the Windows execution contract.
5. Re-run the inventory after fixes and compare counts. Do not label a component operational until the corresponding current evidence passes.

## Acceptance rules

- **Exists:** tracked source/configuration is present.
- **Test-verified:** a test run for the exact revision completed successfully.
- **CI-verified:** a relevant workflow for the exact revision completed successfully.
- **Live-attested:** a fresh external runtime/device observation is available and tied to the exact component and revision.
- **Revenue-verified:** a real transaction/payout or independently checkable pool accounting record exists.

No item advances to a stronger state merely because its source file exists or a different workflow passed.
