# Brain Cloud MAX — Target Architecture Blueprint

Status: DESIGN BASELINE
Scope: Electronic Brain cloud executor / distributed AI compute platform
Source of truth: GitHub repository main branch
Principle: logical resources are software-defined; physical power/cooling/BMC remain provider-owned infrastructure.

## 1. Architecture

BRAIN CONTROL PLANE
- Memory
- Decision Engine
- Security / Permissions
- Task Engine
- Orchestrator
- Audit / Evidence
- Recovery

EXECUTION PLANE
- CPU worker pool
- GPU worker pool
- Storage services
- Video/media workers
- AI inference workers
- Build/test workers

INFRASTRUCTURE PLANE
- Kubernetes
- Container runtime
- KVM/VM layer where required
- VPC/VNet
- Load balancing
- DNS/TLS
- Secrets
- Monitoring
- Backup/DR

## 2. Target node profiles

### Control Plane Node
- 8–32 vCPU
- 32–128 GB ECC-equivalent memory
- Enterprise NVMe
- HA across at least 3 logical replicas for production

### CPU Compute Node
- EPYC-class high-core CPU
- 64–192+ vCPU
- 256 GB–1 TB RAM
- Local NVMe scratch
- Stateless where possible

### GPU Compute Node
- 1–8 accelerator GPUs per node
- NVIDIA Blackwell-class or AMD Instinct-class accelerator
- 64–128+ vCPU
- 512 GB–2 TB RAM
- High-bandwidth GPU interconnect when supported
- Local NVMe scratch

### Storage Node
- NVMe performance tier
- Object-storage capacity tier
- Snapshot/backup tier
- No single-node dependency

### Recovery Node
- Independent recovery/control capability
- Cross-zone backup access
- Able to restore Brain control-plane state

## 3. Resource targets

CPU: scalable to hundreds of logical cores across workers.
RAM: scalable from hundreds of GB to multi-TB cluster aggregate.
GPU: scalable from zero to multiple GPU nodes.
Fast storage: 50–100+ TB aggregate NVMe target.
Archive: object storage, potentially PB-scale.
Network: 100/200/400 Gb/s class where provider hardware supports it.
Cluster fabric: RDMA/InfiniBand or high-speed Ethernet when justified.

These are architectural targets, not claims that one cloud VM provides all resources simultaneously.

## 4. Virtual hardware model

Every executor exposes a normalized capability document:

- cpu.logical_cores
- cpu.architecture
- memory.bytes
- gpu.count
- gpu.model
- gpu.vram_bytes
- storage.fast_bytes
- storage.object_bytes
- network.bandwidth
- network.rdma
- virtualization.kvm
- virtualization.qemu
- security.tpm
- security.secure_boot
- availability.zone_count
- recovery.snapshot
- recovery.cross_region

Brain schedules work against capabilities, not vendor-specific machine names.

## 5. Power / cooling / BMC abstraction

Power, UPS, generators, rack cooling, liquid cooling, pumps, heat exchangers and physical fans are provider-owned.

Brain MUST NOT pretend to control physical cooling unless a provider exposes a supported telemetry/control API.

Brain MAY consume:
- temperature telemetry
- GPU thermal state
- power/energy telemetry
- throttling state
- hardware health
- provider host-health signals

Virtual BMC/firmware state is represented as a management-plane abstraction where supported.

## 6. Software stack

OS: Linux enterprise distribution.
Container runtime: containerd/Docker-compatible runtime.
Orchestration: Kubernetes.
GPU runtime: CUDA or ROCm.
Virtualization: KVM/QEMU where VM isolation is required.
API: HTTPS/API Gateway.
Network: private VPC/VNet + internal service networking.
Secrets: cloud secret manager / vault abstraction.
TLS: automated certificate lifecycle.
DNS: managed DNS.
Logs: centralized immutable/retained logging.
Metrics: CPU/GPU/RAM/disk/network/thermal where exposed.

## 7. Brain services

- brain-control-plane
- brain-orchestrator
- brain-memory
- brain-decision-engine
- brain-task-engine
- brain-permissions
- brain-ai-gateway
- brain-code-agent
- brain-device-bridge
- brain-media-engine
- brain-publishing
- brain-revenue-ledger
- brain-audit
- brain-health
- brain-recovery
- brain-executor-registry

## 8. Execution contract

TASK
 -> CAPABILITY DISCOVERY
 -> EXECUTOR SELECTION
 -> SINGLE-FLIGHT LOCK
 -> EXECUTION
 -> TECHNICAL QC
 -> DOMAIN/CINEMATIC QC when applicable
 -> EVIDENCE
 -> VERIFICATION GATE
 -> ACCEPT / REJECT
 -> RELEASE

No success state is valid without verification evidence.

## 9. Reliability model

Required:
- no duplicate runner sessions
- bounded concurrency
- idempotent orchestration
- health checks
- lease/heartbeat
- automatic stale-executor quarantine
- retry budget
- circuit breaker
- recovery checkpoint
- audit trail
- deterministic deployment identity

Self-healing must be bounded. No unbounded parallel repair loops.

## 10. Availability model

Production target:
- multi-zone control plane
- redundant worker pools
- stateless services where possible
- replicated metadata
- object-storage backups
- cross-zone recovery
- optional cross-region DR

A worker failure must not equal Brain failure.

## 11. Security model

- least privilege
- workload identity
- secret manager
- encrypted storage
- encrypted network paths
- secure boot/virtual TPM where available
- immutable audit logs
- signed release/evidence artifacts
- executor identity
- explicit permission gates for destructive actions

## 12. Cost/feasibility gate

Before provisioning any target:
1. provider quota check
2. regional capacity check
3. GPU availability check
4. network capability check
5. storage capability check
6. expected monthly cost
7. free/low-cost alternative if available
8. fallback executor

The MAX architecture is a capability ceiling, not a requirement to provision the maximum footprint.

## 13. Arkan relationship

Arkan remains Executor-01 / baseline executor.
It is NOT the architectural ceiling.

Arkan can execute:
- Linux/WSL jobs
- GitHub Actions runner jobs
- QEMU experiments
- lightweight Brain tasks

Heavy GPU/large-memory/production workloads should be scheduled to stronger cloud executors when available.

## 14. Acceptance gates

G0: Architecture validated
G1: Executor capability discovery passes
G2: Control plane health passes
G3: Single-flight orchestration passes
G4: CPU worker benchmark passes
G5: GPU worker benchmark passes when provisioned
G6: storage benchmark passes
G7: network benchmark passes
G8: failure/recovery test passes
G9: backup/restore test passes
G10: end-to-end Brain task passes

Only after G10 may the environment be marked BRAIN_CLOUD_MAX_READY.

## 15. Next implementation phase

1. Implement executor capability schema.
2. Implement executor registry.
3. Implement capability-based scheduler.
4. Implement cloud node profiles.
5. Implement health/heartbeat/lease.
6. Implement bounded recovery.
7. Implement infrastructure manifests.
8. Add provider adapter layer.
9. Run benchmark/evidence gates.
10. Select the strongest feasible cloud provider footprint based on measured capacity, quota and cost.

