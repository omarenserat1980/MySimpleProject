# Platform Foundation Architecture — V2

## Boundary
`platform_foundation/` is the independent software foundation. It is not Brain and must not import Brain.

## Verified base layers (phase 4-3)
1. Core Runtime
2. State
3. Job execution
4. Audit/Evidence
5. Health reporting

## Phase 4-4 security/failure/recovery layer
- **Security:** explicit actor/action grants; protected jobs deny by default; grants are in-memory and auditable only through the caller's surrounding evidence.
- **Failure:** conservative classification, retryability metadata, and no implicit retries.
- **Recovery:** integrity-checked JSON-compatible state checkpoints and evidence-backed restore/rejection events.
- **State isolation:** deep copies at set/get/snapshot/restore boundaries.

## Planned expansion
Persistent configuration and storage -> identity and durable authorization -> API -> events -> worker isolation -> observability -> durable recovery -> plugin/agent runtime.

## Integration boundary
Brain integration occurs only through explicit adapters after the platform gates pass. Brain must not become the foundation's hidden dependency.

## Failure and recovery limits
A foundation failure must be observable and must not be converted into synthetic success. Current checkpoints are process-local memory objects; they do not survive process restart and must not be described as backups. No automatic retry or destructive recovery is performed.
