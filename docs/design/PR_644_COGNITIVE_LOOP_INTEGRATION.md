# PR #644 CognitiveLoop Integration Contract

Status: preparation only. This document does not merge PRs or claim the integration has been implemented.

## Verified branch overlap

The current Universal Design Factory branch adds `DesignFactoryAdapter` and the `design.plan` catalog/dispatch path in `brain_v12/brain/cognitive_loop.py`.

The Bitcoin North Star branch adds `EngineeringFactory`, the `engineering.propose` catalog/dispatch path, and a mission-alignment gate in the same file. Its `DecisionEngine` also normalizes the North Star command and assesses mission alignment.

These are independent features touching the same orchestration file. Taking either branch's file wholesale would drop the other branch's behavior.

## Required integration shape

1. Preserve both imports and initialize both adapters/factories:
   - `DesignFactoryAdapter` for `design.plan`
   - `EngineeringFactory` for `engineering.propose`
2. Keep both catalog entries and both dispatch handlers. Keep their result envelopes compatible with the existing `TOOL_SELECTED` and `TOOL_RESULT` events.
3. Preserve the Bitcoin North Star mission-alignment gate before creating tasks or dispatching work. An `OFF_COURSE` result must remain a fail-closed return, not silently continue into execution.
4. Preserve the design factory's explicit simulation authorization contract. Simulation must remain labelled `SIMULATED`; it must not become hardware, mining, accepted-share, payout, or revenue evidence.
5. Preserve Engineering Factory's evidence/proposal behavior and permission boundaries. A proposal is not implementation or verification.
6. Keep the integration tests deterministic and local; do not require a phone, remote worker, miner, cloud executor, paid service, network access, or secrets.

## Acceptance checks before either PR is merged

- The tool catalog exposes both `design.plan` and `engineering.propose`.
- `execute_tool` dispatches both paths and publishes the normal selection/result events.
- The North Star gate blocks off-mission work before task creation or tool dispatch.
- Design Factory plan-only remains the default; simulation requires the existing explicit opt-in parameters.
- A simulated result can never be promoted to real-device, accepted-share, payout, or revenue evidence.
- Relevant PR checks pass on the exact final integration head; cancelled checks are not treated as passes.
- Review the final diff for unintended changes to the existing cognitive loop, decision policy, evidence stores, and permissions.

## Current decision

Keep PR #658 and PR #644 open and separate while preparing a dedicated integration candidate. No merge to `main` is authorized by this document. Do not report physical ASIC manufacture, real Bitcoin mining, accepted shares, payouts, or revenue without independent evidence from the corresponding real system.
