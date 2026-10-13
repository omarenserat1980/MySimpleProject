# Family-Governed Task Queue

`FamilyGovernedTaskService` is the required policy-aware entry point for adding work to the persistent node queue. It checks task type, evaluates the family policy before enqueue, and records a bounded decision event in its in-process audit list.

## Current task policy

- `health_check` and `network_self_test`: low-risk local/simulated checks, no guardian approval.
- `write_text`: local sandbox workspace change, currently medium risk.
- `run_brainvm`: bounded BrainVM-1 program, currently medium risk.
- `read_text`: treated as high-risk private-data access and requires a verified, action-scoped guardian approval.
- Unknown tasks, shell commands, and tasks outside the node allowlist are rejected.

## Integration and trust boundary

Use `FamilyGovernedTaskService(queue).enqueue(...)` rather than calling the raw queue API from orchestration/API code. The raw `PersistentTaskQueue` remains a low-level storage primitive, so the service must be wired into every production enqueue route before claiming end-to-end enforcement. The audit list is in memory and is not yet a durable audit ledger.

`FamilyApproval.identity_verified` is a trust assertion, not authentication performed by this package. Do not accept approval objects directly from untrusted HTTP or task payloads. A production integration must obtain the approval from a trusted identity/consent provider, persist verifiable approval evidence, and bind it to the exact task/action. Until that exists, private-data access must fail closed.

Family policy is separate from the real Windows boot gate. No family approval by itself proves guest boot. This integration creates no paid resources, external network access, or physical-device access.
