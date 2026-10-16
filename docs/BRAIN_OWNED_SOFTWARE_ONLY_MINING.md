# Brain-Owned Software-Only Mining Contract

## Canonical rule

Electronic Brain owns mining orchestration and, when implemented, the mining compute runtime. A phone, desktop, Termux session, ASIC, GPU, or other physical device may serve only as a connectivity, control, or read-only observation gateway. Physical devices must not be selected as the mining compute host, and external miner processes are not an allowed fallback.

## Current implementation status

- `brain_v12/brain/brain_owned_mining_contract.py` expresses the policy, planning, execution gate, and evidence classification.
- `brain_v12/brain/mining_controller.py` produces Brain-owned software-only plans and blocks execution until a native Brain-owned backend exists.
- `brain_v12/brain/cloud_mining_control_plane.py` accepts only software-node kinds, creates plan-only jobs, and blocks admission until the native backend exists.
- The controller does not install or launch miner software and does not contact a mining pool.
- The current backend is **NOT IMPLEMENTED**. A plan, test pass, online gateway, or successful API response is not proof of mining.
- GitHub Actions must not run mining workloads. Simulators may test orchestration and evidence rules only.

## Required sequence before real mining

1. Implement a bounded Brain-owned compute backend in a separately reviewable software execution environment. Do not use the connected user's device or a physical miner as the compute host.
2. Independently review algorithm support and realistic compute requirements. Bitcoin SHA-256d software execution without suitable dedicated compute is not a credible profitability promise.
3. Add resource, runtime, cancellation, secret-injection, pool endpoint, and authority controls. Credentials must never enter source control, logs, task payloads, or evidence files.
4. Require explicit user approval before any real pool connection or mining start.
5. Verify worker identity, pool-reported accepted shares and hashrate, and provenance linking that evidence to the Brain-owned runtime. A payment or profit claim needs separate independent payment and cost evidence.

## Evidence semantics

- `SIMULATION_ONLY`: never counts as real mining.
- A gateway heartbeat: proves liveness only, not mining capability.
- A miner process: proves process presence only, not accepted shares.
- Pool API telemetry: can support real activity only when independently verified and bound to an attested Brain-owned compute runtime.
- Accepted shares do not prove payout; payout does not prove profit.

## Safety guarantees

The plan and gate functions are policy-only and do not execute mining. External miner execution, physical-device computation, GitHub Actions mining, pool contact, and production setting changes remain disabled until a separately reviewed implementation and explicit authorization exist.
