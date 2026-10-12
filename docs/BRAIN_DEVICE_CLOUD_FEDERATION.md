# Brain Device Cloud Federation

Status: safe planning foundation; live device and cloud execution are not yet proven.

## Fleet profiles

- **Arkan** — canonical software-defined computer `arkan-virtual-01`, backed by Brain simulator. It is not the ASUS VivoBook or a Windows runner. Only bounded symbolic simulation is eligible after live simulator boot and smoke-task evidence; Windows Server 2025 remains unverified. A physical host, if used, must have a distinct `arkan-host-*` ID.
- **Brain virtual phone** — software-only phone profile `phone-virtual-01`, displayed as **هاتف برين الافتراضي**. The fleet indicator selects this logical node instead of Desktop Commander/TRIGGERcmd. It does not claim that an Android OS or emulator process is running; `execution_eligible` stays false until independent simulator boot and bounded task evidence are supplied.
- **Redmi** — Android/Termux agent profile using the known logical ID `redmi3-01`. This registry entry is not a live heartbeat.
- **Realme** — Android endpoint placeholder `realme-pending-identity`. Do not route missions to it until discovery confirms its model and actual agent ID.
- **Honda e:NP1 2023 / Honda CONNECT** — companion client for information and synchronization only. It is not a compute worker. Do not modify firmware, bypass region/carrier restrictions, or send commands to safety-critical vehicle systems.

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

The authenticated endpoint `GET /api/device/cloud-federation/status` combines the current DeviceBridge heartbeat snapshot with the logical fleet profiles. The response field `active_software_node` points the status indicator to `phone-virtual-01` (`هاتف برين الافتراضي`) and explicitly reports `reality=SIMULATED` and `physical_device_required=false`. This is a selected software profile, not a claim of a live Android OS. It requires the Brain control credential. It reports `ONLINE`, `STALE`, or `NOT_OBSERVED` for known Android agent IDs, but deliberately keeps `identity_verified=false` and `execution_eligible=false`: the shared agent credential and heartbeat are not a unique hardware identity proof. The canonical Arkan row is `NOT_PROVISIONED`, `CONFIGURED_NOT_RUNNING`, or `SIMULATION_READY` based on the persisted identity and live in-process simulator/task evidence; this never means native OS boot. Physical host heartbeats do not set Arkan identity or execution eligibility. Honda remains `NOT_OBSERVED` unless a dedicated verified telemetry adapter is implemented. Cloud capacity remains `NOT_PROBED` and paid provisioning remains disabled.

## Current limitation / next proof gate

This code provides a deterministic planning contract and tests only. It does not yet connect the registry to the live Agent Gateway or provision a cloud VM. The next gate is to pass Arkan provisioning/fleet CI and verify the live status endpoint after provisioning, then run a harmless end-to-end simulation task. Discover the Realme agent identity separately if that Android endpoint is still needed. Windows Server 2025 is not considered deployed until the guest is reachable and boot evidence is captured.
