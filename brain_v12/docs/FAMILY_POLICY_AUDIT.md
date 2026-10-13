# Durable Family Policy Audit

Every admission decision and denial is written to the same local SQLite database as the software-node queue. Events form a SHA-256 hash chain (`previous_hash` → `event_hash`) and can be checked with `FamilyGovernedTaskService.audit_status()` or `FamilyPolicyAudit(database_path).verify()`. Agent status exposes the current chain verification result.

## Approval replay protection

Approval consent references are consumed once in a SQLite table with a uniqueness constraint. Reusing the same reference is rejected before another task is queued. Task fingerprints are recorded alongside the consumption event. The approval still must match guardian role, verified-identity assertion, non-empty consent reference, and exact action scope.

## Important security limits

This is a tamper-evident hash chain, **not a digital signature**. Anyone able to rewrite the database and recompute the entire chain can forge it. Production signing requires a protected signing key or external append-only audit sink. The `identity_verified` field remains an assertion supplied by a trusted caller, not authentication performed by this code. Do not accept approval objects from untrusted client payloads. Until a trusted identity/consent verifier is integrated, sensitive operations must remain fail-closed.

The audit database is local to the configured filesystem; it is not distributed or backed up automatically. This feature creates no cloud resources, network access, physical-device access, or proof of Windows Server 2025 boot.
