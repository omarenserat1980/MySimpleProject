# Brain Device Cloud Federation

Status: software-only active fleet and evidence-backed indicator contract; native guest execution remains separately gated.

## Fleet profiles

- **Arkan** — canonical software-defined computer `arkan-virtual-01`, backed by Brain simulator. The fleet status indicator and the logical replacement for Desktop Commander/TRIGGERcmd target this software node, not the physical ASUS VivoBook. Only bounded symbolic simulation is eligible after live simulator boot and smoke-task evidence; Windows Server 2025 remains unverified. A physical host, if used, must have a distinct `arkan-host-*` ID.
- **Brain virtual phone** — software-only phone profile `phone-virtual-01`, displayed as **هاتف برين الافتراضي**. It remains a separate unselected profile. It does not claim that an Android OS or emulator process is running; `execution_eligible` stays false until independent simulator boot and bounded task evidence are supplied.
- **Legacy physical endpoints** — `redmi3-01`, Realme identifiers, physical host IDs, and vehicle clients are not members of the active software fleet and cannot receive work through the software-only router. Historical audit records may retain these identifiers, but active status indicators must not present them as Brain software nodes.

## Cloud capacity layer

The Cloud Hardware Fabric models CPU, RAM, storage, network, and optional GPU. The planner may recommend a cloud SKU, but it does not create resources. Cloud execution is eligible only after all of these are independently proven:

1. Current provider/account entitlement and region/SKU eligibility.
2. Required CPU/RAM/storage/network capacity is available now.
3. The free-cost gate passes; paid provisioning stays disabled by default.
4. A cloud executor is enrolled with authenticated identity and fresh heartbeat.
5. A real task completes and produces verifiable evidence tied to its task ID and source revision.

## Scheduling rules

- Prefer a verified local executor when its declared capabilities fit.
- Otherwise use the cloud pool only when both capacity evidence and the free-cost gate pass.
- Do not infer device identity or liveness from a configured name, queued job, green CI run, or old heartbeat.
- Keep secrets out of device manifests and logs.
- Store backups separately from working storage and verify restore evidence.
- Do not treat cloud storage as RAM/CPU; actual compute requires a VM/container/remote worker.
- Vehicle integration is limited to companion/information workflows. No vehicle-control or safety-system commands are scheduled.

## Read-only status API

The authenticated endpoint `GET /api/device/cloud-federation/status` uses canonical software-node profiles and simulator evidence. The `active_software_node` indicator targets `arkan-virtual-01` and explicitly reports `reality=SIMULATED` and `physical_device_required=false`. This is a selected software profile, not proof of a running native OS. The active fleet includes only Brain software nodes; physical Android agents, physical hosts, and vehicle clients are excluded from active indicators and execution routing. Arkan may report `NOT_PROVISIONED`, `CONFIGURED_NOT_RUNNING`, `DEGRADED`, or `SIMULATION_READY` based on canonical identity, simulator runtime evidence, and a passing bounded task. `SIMULATION_READY` never means native OS boot. Cloud fallback is disabled in the software-only router; cloud capacity indicators remain unverified unless a separately authorized Brain-managed backend contract is introduced.

## Indicator contract

The canonical indicator engine in `brain_v12/brain/canonical_indicators.py` records subject identity, source, backend, observation/verification timestamps, verification level, evidence references, freshness, and machine-readable error codes. Missing observations are `UNKNOWN`; stale observations are `STALE`; insufficient evidence is `UNVERIFIED`. Required-indicator aggregation exposes blockers rather than hiding them behind a green aggregate.

Execution planning accepts only verified Brain virtual-computer or virtual-phone endpoints. Physical host, Android-agent, and vehicle roles are rejected by the default software-only policy. Cloud fallback is not a substitute for an internal software node and remains disabled by this router.

## Current limitation / next proof gate

The indicator engine and policy tests establish code-level contracts; they do not by themselves prove that a persistent simulator process or Windows guest is running. Verify the targeted CI, then provision and run the canonical Arkan simulator and capture a bounded task result. Windows Server 2025 is not considered deployed until a compatible guest-execution backend returns fresh guest OS identity, boot, heartbeat, and health evidence.
