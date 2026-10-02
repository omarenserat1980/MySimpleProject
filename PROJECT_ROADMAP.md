# Electronic Brain — Roadmap

## Phase 1 — Evidence and runtime foundation
- [x] GitHub source-of-truth workflow
- [x] Brain GitHub Cloud control-plane workflow
- [x] Bounded Brain task runner
- [x] Master evidence-first audit
- [x] Self-healing and supervisor modules
- [x] Keep audit commands import-safe across CI and local execution
- [ ] Make failed tasks emit diagnostic evidence before workflow termination

## Phase 2 — Autonomous inspection and repair
- [ ] Watch recent workflow runs automatically
- [ ] Fetch failed job logs and artifacts
- [ ] Classify failures
- [ ] Select a bounded repair strategy
- [ ] Apply only approved repair scopes
- [ ] Commit repair
- [ ] Rerun affected workflow
- [ ] Verify result and record evidence
- [ ] Stop after bounded attempts

## Phase 3 — Brain Cloud execution
- [x] Free GitHub-hosted Linux runner
- [x] Python runtime
- [x] FFmpeg/FFprobe installation
- [x] espeak-ng installation target
- [x] Stable media toolchain verification target
- [ ] Durable run/evidence index
- [ ] Unified executor contract

## Phase 4 — Cinematic Factory
- [x] Deterministic cinema pipeline tests
- [x] Media health and self-healing gates
- [ ] Real local render task exposed through Brain Runner
- [ ] Real artifact QC with ffprobe
- [ ] Master QC
- [ ] Verified final MP4 artifact
- [ ] YouTube publishing only after explicit authorization and OAuth verification

## Phase 5 — Device bridge
- [x] Device bridge modules
- [ ] BRAIN Termux Emulator as primary phone-side executor
- [ ] Secure polling/command contract
- [ ] Offline queue and recovery
- [ ] Phone-to-Brain Cloud evidence synchronization

## Phase 6 — Knowledge and Quran layer
- [x] Reasoning guard
- [x] Knowledge pipeline modules
- [x] Layer audit
- [ ] Complete registry build and evidence verification
- [ ] Immutable audit trail for generated knowledge

## Phase 7 — Economic and opportunity systems
- [x] Economic ledger safety model
- [x] Opportunity workflow modules
- [ ] Evidence-backed opportunity normalization/deduplication
- [ ] Payment adapters kept separate from discovery
- [ ] No transaction without explicit permission and verified receipt

## Phase 8 — Production hardening
- [ ] Security review
- [ ] Permission minimization
- [ ] Recovery chaos tests
- [ ] Artifact retention policy
- [ ] End-to-end release gate

## Phase 9 — Customer learning and operational quality
- [x] Durable customer feedback lifecycle
- [x] Evidence-gated feedback resolution
- [x] Canonical Diwan API routes (duplicate implementations removed)
- [x] Cinema publication fail-closed gate
- [ ] Connect verified outbound customer transport
- [ ] Link feedback automatically to Diwan case files and improvement tasks
- [ ] Add abuse/rate limiting and persistent public API storage
- [ ] Establish end-to-end release gate
