# Windows Server 2025 Simulation Factory

## Purpose and boundary

The Simulation Factory models Windows Server 2025 boot behavior inside Electronic Brain. It is a deterministic software model; it does not boot Windows, launch QEMU/Hyper-V, download installation media, call Azure/OpenNebula, contact physical hosts, or create cloud resources.

Every report includes:

- `execution_mode: "SIMULATION_ONLY"`
- `real_windows_boot_verified: false`
- `host_observed_resources.status: "NOT_COLLECTED"`
- Synthetic event evidence with a SHA-256 hash chain.

A hash chain detects accidental or unauthorized mutation within the supplied event sequence. It is not a digital signature, a trusted timestamp, or proof of an actual operating system boot.

## Existing building blocks inspected

The repository already contains a logical virtual hardware layer in `brain_v12/virtual_hardware/`, a `WindowsServerVM` contract, a UEFI model, sparse virtual disk model, and an Azure VM planning simulator. The new factory adds a separate behavior state machine and evidence chain; it does not replace or silently promote those components into a real Windows runtime.

## Run a simulation

From the repository root:

```bash
PYTHONPATH=. python - <<'PY'
import json
from brain_v12.brain.windows_server_2025_simulation_factory import simulate_windows_server_2025
report = simulate_windows_server_2025("success")
print(json.dumps(report, indent=2))
PY
```

Available scenario IDs are exported as `SCENARIOS` by the simulator module. They cover success, boot-disk/configuration errors, resource exhaustion, service and network faults, restart, simulated power-loss recovery, timeout, invalid routing, and evidence tampering.

Run focused tests:

```bash
PYTHONPATH=. python -m unittest brain_v12.tests.test_windows_server_2025_simulation_factory -v
```

## Protected API

The API is registered under `/api/simulations/windows-server-2025`. It requires the existing `X-Brain-Control-Key` control-plane header. Endpoints create a run, read its summary, inspect events, and retrieve the report.

Reports are atomically persisted as local JSON files under `BRAIN_SIMULATION_STATE_DIR` (default: `.brain/state/windows_server_2025_simulations`) and can be reloaded after an API process restart. This is a local evidence store, not yet an integration with the canonical Brain Memory/EvidenceStore; do not claim cross-device synchronization or tamper-proof remote retention.

Example request:

```http
POST /api/simulations/windows-server-2025
X-Brain-Control-Key: <configured control key>
Content-Type: application/json

{"scenario_id":"success","hardware":{"vcpu_count":2,"ram_mib":4096,"disk_gib":64}}
```

The API rejects unknown scenario IDs and unknown virtual-hardware fields. It never accepts a caller-selected real executor or a real-boot capability. The dashboard is served at `/api/simulations/windows-server-2025/dashboard`; the page keeps the supplied control key in page memory only and does not store it in localStorage. JSON reports are available at `/{run_id}/report`, event streams at `/{run_id}/events`, and human-readable Markdown at `/{run_id}/report.md` beneath the API prefix. Reads re-verify the persisted event chain before returning evidence.

## Scenario semantics

- `SIMULATED_BOOT_SUCCESS`: the model completed its defined stages and the synthetic evidence chain verified.
- `SIMULATED_BOOT_FAILED`: a modeled stage failed or evidence verification failed.
- `SIMULATED_BOOT_PARTIAL`: reserved for a future supported partial-mode contract; not emitted as a successful full boot.
- `BLOCKED`: the scenario, capability, or preflight contract is invalid.
- `CANCELLED`: the scenario models cancellation.

A scenario named `power_loss_recovery` means a state-model recovery path passed; it does not imply Windows recovered from a real power loss.

## Safety and limitations

The simulator is separate from `windows-server-2025-real-boot` and `windows-server-2025-cloud-native`. Attempting to select either capability is blocked. The behavior model does not execute a Windows kernel, Windows Boot Manager, Windows drivers, or actual Windows services.

The dashboard, durable run history, Brain Memory integration, and broader end-to-end workflow are not claimed complete by this increment. Verify the API routes and all CI checks before merging. Never interpret this simulator's result as real-boot evidence.


## Weighted implementation progress

Simulation reports now include `implementation_progress`, produced by
`brain_v12/brain/windows_server_2025_simulation_progress.py`. The roadmap is
weighted to 100 points and currently reports **30% implementation coverage**:
four implemented milestones are complete:

1. Simulation-only safety boundary.
2. Virtual hardware model and preflight validation.
3. Boot-stage state machine and failure injection.
4. Deeper firmware and boot-configuration semantics, including fail-closed UEFI/boot-disk validation.

The remaining 70 points are explicitly pending and listed in the report. This is
a transparent project checklist, not an estimate of the probability of booting,
not a Windows compatibility score, and not real boot evidence. The simulator
continues to report `real_windows_boot_verified: false`. Future percentage
increases must follow implementation, tests, and evidence for additional
milestones; do not manually raise the displayed value.
