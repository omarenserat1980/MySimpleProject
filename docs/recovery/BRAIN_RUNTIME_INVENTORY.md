# Brain Runtime Inventory

## Canonical runtime
- FastAPI application: brain_v12/app.py
- Default local URL: http://127.0.0.1:8012
- Runtime version observed in project: V14
- Supervisor is single-instance and writes evidence/history under .brain/state.

## Core persistent state
- BRAIN_DB defaults to brain_v12/brain_v12.db in the application when no override is provided.
- BrainSyncStore replica default: brain-cloud.
- BRAIN_SYNC_QUEUE defaults to brain_v12/.brain/state/sync_queue.jsonl when no override is provided.
- EvidenceStore default: brain6_artifacts/evidence/evidence.db.

## Recovery-relevant concepts
- MemoryStore: memories, goals, messages, events, state, revenue/opportunity history, incidents and device task state.
- DurableSyncQueue: restart-safe event queue with replay and acknowledgements.
- EvidenceStore: append-only evidence with canonical SHA-256 verification.
- DeviceBridge: executor boundary; devices are replaceable.

## Runtime API families documented in the project
- /health
- /api/device/status
- /api/device/heartbeat
- /api/system/readiness
- /api/brain/liveness
- /api/brain/life-certificate
- /api/agent-gateway/*
- /api/brain/evidence/*

## Important semantic distinction
/health is a cloud-worker attestation contract. Local Brain liveness is assessed separately by the Brain liveness endpoints. A NOT_RUNNING cloud-worker attestation does not by itself mean the local Brain process is dead.

## Recovery safety
No recovery workflow may copy secret values into Git artifacts. State snapshots must be integrity-checked and tied to a source commit/schema before restore.
