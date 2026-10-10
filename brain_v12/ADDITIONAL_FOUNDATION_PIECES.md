# Additional Brain foundation pieces

These are initial standalone skeletons only, added on the same feature branch.

- \`task_envelope.py\`: provider-neutral task request contract with schema version, idempotency key, intent hash, capability scope, and a strict zero-cost ceiling.
- \`resource_health.py\`: pure heartbeat freshness classifier. It does not contact or enroll any device.
- \`execution_evidence_bundle.py\`: deterministic metadata bundle and SHA-256 digest. It does not sign evidence or assert that execution was verified.

These complement existing TaskEngine, DeviceBridge, permissions, and EvidenceStore code; they do not replace or integrate with those components yet.
