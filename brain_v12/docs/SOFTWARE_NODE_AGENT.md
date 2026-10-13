# Persistent Software Node Agent

The `SoftwareNodeAgent` builds on `InitialSoftwareNode` with a local SQLite-backed task queue and a cooperative heartbeat thread.

## Included behavior

- Durable queue records on the same local filesystem (`LOCAL_SQLITE`); pending tasks survive agent/process recreation when the same database path is reused.
- An allowlist matching the node's sandbox task types. Shell, PowerShell, arbitrary URLs, remote execution, and Windows boot tasks are rejected at enqueue time.
- Idempotency keys to deduplicate client retries.
- Transactional claims with lease tokens; an expired lease returns a task to `PENDING` and permits another attempt.
- Persisted task status/results (`PENDING`, `RUNNING`, `COMPLETED`, `FAILED`) and attempt counts.
- A stoppable heartbeat thread records a monotonically increasing sequence, timestamp, and simulated node state in SQLite.
- `run_once()` performs one bounded queue poll and task execution. The autonomous worker thread repeatedly claims and executes allowlisted tasks until stop() is called; run_once() remains available for one explicit poll.

## Example

```python
from pathlib import Path
from brain_v12.brain.software_node_agent import SoftwareNodeAgent

agent = SoftwareNodeAgent(
    Path("./brain-node-workspace"),
    database_path=Path("./brain-node-state/queue.sqlite3"),
    heartbeat_interval=5.0,
    poll_interval=0.25,
)
agent.enqueue({"type": "health_check"}, idempotency_key="initial-health-check")
agent.start()
try:
    # The worker thread drains the local queue automatically.
    print(agent.status())
finally:
    agent.stop()
```

## Durability and delivery semantics

The SQLite database is durable only to the extent that the chosen local filesystem is durable and remains available. This is not a replicated or distributed queue. Leases provide **at-least-once** execution: if a worker crashes after performing a side effect but before saving its result, a later worker may retry that task. Use idempotency keys for enqueue retries and make task effects idempotent where possible. There is no exactly-once guarantee.

## Explicit boundaries

- No host/physical hardware contact, sockets, host NIC, external network, cloud provisioning, shell execution, or paid services.
- Heartbeat means a local persisted liveness record, not proof that a remote controller can reach the node.
- CPU/RAM/network are software simulations; GPU remains unavailable and no acceleration is claimed.
- This worker executes only the existing allowlisted sandbox tasks and BrainVM-1 programs. It does not execute native x86/ARM code.
- `windows_server_2025_boot_verified` remains false. A real Windows Server 2025 boot is a separate milestone requiring an available execution backend and evidence collected inside the guest OS.

## Family governance

Use `agent.enqueue(...)` as the admission path. It routes requests through `FamilyGovernedTaskService` and records durable policy audit events. `run_once()` performs a second policy check after claiming a task and before invoking the node executor. This blocks high-risk tasks without persisted trusted execution-authorization evidence and catches unknown task types inserted or altered through the raw SQLite queue. Denied tasks are marked `FAILED` without calling the executor.

Do not expose `agent.queue.enqueue(...)` to untrusted callers; it remains a low-level storage primitive and can bypass admission checks, even though execution rechecks policy. The default approval verifier rejects self-asserted identity. High-risk tasks such as `read_text` remain denied at execution until a trusted, durable, independently verifiable execution-authorization record is implemented. The local hash-chain audit is tamper-evident, not a digital signature or external immutable backup.
