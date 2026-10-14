# Brain Digital Lab — Universal Governance

Status: proposed implementation contract; not evidence that all assets are already inventoried, tested, or modified.

## Mission

Brain Digital Lab (BDL) is the required engineering intake, assessment, development, verification, and release gate for every known Electronic Brain V12/V13 component. Scope includes source code, services, APIs, automations, scripts, apps, plugins, AI agents, device bridges, firmware, RTL/ASIC designs, infrastructure definitions, servers, and physical-device configurations.

## Non-negotiable rules

1. Inventory before claiming coverage. Discover assets from repository trees, manifests, workflow definitions, service registries, device-agent reports, and deployment metadata. Mark unknown or unreachable assets as UNVERIFIED; never silently count them as covered.
2. Every asset has an owner, type, source/location, version or fingerprint, dependencies, risk tier, test plan, last evidence timestamp, status, and next action.
3. Every proposed change follows: DISCOVER → BASELINE → PLAN → ISOLATED CHANGE → TEST → SECURITY/SAFETY REVIEW → ACCEPT/REJECT → RELEASE/ROLLBACK → EVIDENCE.
4. No automatic merge to main, production deployment, destructive action, device firmware flash, server reconfiguration, secret rotation, external-provider activation, or spending without the applicable explicit approval and policy gate.
5. Preserve backups and a rollback path before high-risk changes. Use least privilege and isolated workspaces. Do not expose secrets in logs or artifacts.
6. Prefer free and open-source tools and zero-cost execution. Do not buy or activate paid resources; report BLOCKED if a required capability is not available for free.
7. Do not claim physical hardware was upgraded because a simulation or software change passed. Hardware work is divided into: (a) software/firmware/configuration, (b) RTL/FPGA/ASIC design and simulation, (c) hardware-in-the-loop tests on a real accessible device, and (d) physical manufacturing and independent acceptance. Report each separately.
8. A successful CI job is evidence only for the checks and commit it actually ran. GDSII is a physical-design artifact, not proof of fabricated or tested silicon.
9. All results must be reproducible where practical and include commit SHA, tool versions, commands/workflow run, test outcomes, artifacts, known limitations, and timestamp.
10. If a component cannot be reached or safely tested, record the reason and an explicit follow-up; do not fabricate evidence.

## Required asset domains

- Core Brain runtime, memory, decision/task engines, permissions, APIs, web UI, AI gateway, and orchestration.
- Scripts, CLI utilities, self-healing/evolution modules, tests, dependency manifests, build tools, and CI workflows.
- Apps, Android APKs, web applications, publishing/video/media pipeline, and integrations.
- Agents and device bridges, including Termux/Android and Windows runners; stale/offline agents remain unverified.
- ASIC/RTL, testbenches, lint, simulation, formal/differential verification, synthesis, physical design, and GDSII evidence.
- Servers, VMs, containers, deployment manifests, storage, networking, monitoring, backups, recovery, and security configuration.
- Physical hardware inventory and capabilities, firmware, drivers, telemetry, and hardware-in-the-loop evidence.

## Required lifecycle statuses

DISCOVERED, BASELINED, PLANNED, IN_PROGRESS, TESTING, ACCEPTED, REJECTED, BLOCKED, UNVERIFIED, RETIRED.

No asset may be labelled ACCEPTED without linked, recent evidence and a defined acceptance test.

## Acceptance gates

- Inventory gate: scope and unknowns are recorded.
- Baseline gate: current state, versions, health, and existing failures captured.
- Change gate: change is isolated, reviewable, and reversible.
- Verification gate: relevant tests pass; security, regression, and compatibility checks are satisfied for the risk tier.
- Release gate: authorized release path and rollback plan are present.
- Evidence gate: machine-readable summary and artifact links are retained.

High-risk changes require human approval. The lab may autonomously perform read-only discovery, static analysis, safe tests, and proposed patches within a disposable branch/workspace. It must not grant itself broader permissions.

## Rollout plan

1. Establish the inventory schema and read-only discovery report.
2. Inventory repository modules, scripts, workflows, apps, services, ASIC assets, and infrastructure manifests.
3. Add per-domain baselines and tests, starting with critical runtime and security paths.
4. Add CI checks that validate the inventory and require evidence for changed assets.
5. Introduce controlled repair proposals on feature branches; run tests before requesting review.
6. Add device/server integrations only where reachable, authenticated, and explicitly authorized.
7. Expand coverage incrementally; publish a coverage report that distinguishes verified, blocked, stale, and unknown assets.

## Definition of done

The initiative is not complete merely because this document exists. Completion requires an inventory of all discoverable assets, explicit unknowns, working tests for each supported domain, CI evidence, reviewable changes, and a verified rollback procedure. Hardware and server coverage must state whether each result is simulated, software-only, hardware-in-the-loop, or physically manufactured/tested.