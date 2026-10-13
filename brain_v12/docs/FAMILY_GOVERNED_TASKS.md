# Family-Governed Task Queue

`FamilyGovernedTaskService` is the policy-aware admission entry point for adding work to the persistent software-node queue. The agent also repeats policy checks immediately before executing every claimed task.

## Current task policy

- `health_check` and `network_self_test`: low-risk local/simulated checks.
- `write_text`: local sandbox workspace change, currently medium risk.
- `run_brainvm`: bounded BrainVM-1 program, currently medium risk.
- `read_text`: high-risk private-data access; admission requires a scoped approval accepted by an injected verifier.
- Unknown tasks, shell commands, and tasks outside the node allowlist are rejected.

## Two enforcement points

1. **Admission:** call `agent.enqueue(...)` or `FamilyGovernedTaskService.enqueue(...)`. The service validates the allowlist, evaluates policy, records a durable policy-audit event, and queues only allowed tasks.
2. **Execution:** `SoftwareNodeAgent.run_once()` calls `authorize_execution(...)` after claiming a task and before invoking the node executor. This catches legacy/raw-queue insertions and task JSON altered in SQLite. Denied tasks are marked `FAILED` with `executed: false`; the executor is not called.

The raw `PersistentTaskQueue.enqueue(...)` method remains a low-level storage primitive and can bypass the admission decision, but it cannot bypass the agent's execution-time policy recheck. Do not expose raw queue access to untrusted callers.

## Approval evidence boundary

Approval metadata is deliberately not embedded in task JSON. The default `DenyAllFamilyApprovalVerifier` rejects self-asserted identity. Although tests may inject a test-only verifier to exercise admission behavior, the execution gate denies high-risk tasks until a trusted, durable, independently verifiable execution-authorization record is implemented. This means private `read_text` tasks fail closed at execution today, including tasks admitted by a test-only verifier.

The local SQLite audit chain is tamper-evident and can be verified across service recreation, but it is not a digital signature or an external immutable log. Production identity authentication, signed consent evidence, protected signing keys, and external audit backup are not provided by this module.

## Explicit boundaries

Family policy is separate from the real Windows boot gate. Family approval does not prove guest boot. This integration creates no paid resources, external network access, or physical-device access. Windows Server 2025 boot remains unverified.
