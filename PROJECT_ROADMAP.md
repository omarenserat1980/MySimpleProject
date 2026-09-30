# Electronic Brain — Roadmap

## Phase 0 — Foundation
- [x] Control Plane
- [x] Authorization Gate
- [x] Economic Ledger
- [x] Film Supervisor
- [x] Worker heartbeat
- [x] Worker registry
- [x] Job leases
- [x] Local Worker Bridge
- [x] CI smoke tests

## Phase 1 — Real Dispatcher
- [x] Durable job record
- [x] Capability matching
- [x] Lease-aware assignment
- [x] bounded retry policy
- [x] evidence envelope
- [x] status inspection

## Phase 2 — Real execution
- [ ] Connect a user-owned long-running Brain worker
- [ ] Register its capabilities
- [ ] Execute a real non-sensitive job
- [ ] Return evidence to the control plane
- [ ] Verify lease expiry behavior

## Phase 3 — Cinematic production
- [ ] Dispatcher routes film jobs to a capable media worker
- [ ] FFmpeg/FFprobe QC
- [ ] Stage 7 before every production
- [ ] repair/retry trace
- [ ] verified artifact digest
- [ ] real-image/audio pipeline where an available free backend exists

## Phase 4 — Brain operations
- [ ] Health/status dashboard
- [ ] persistent queue metrics
- [ ] audit viewer
- [ ] worker capability inventory
- [ ] failure/retry dashboard

## Phase 5 — Learning and architecture
- [ ] research evidence store
- [ ] architecture proposals
- [ ] proposal validation
- [ ] controlled merge workflow
- [ ] regression protection

## Phase 6 — Optional external actions
Only after authorization:
- external submission
- publication
- contracts
- payment adapter execution
- withdrawal

These are never prerequisites for the Brain core.
