# Local Worker Recovery

The Brain Local Worker uses four durable filesystem states:

- queued
- running
- completed
- failed

If a worker process dies while a job is in running, the next worker instance recovers the job to queued after BRAIN_LOCAL_WORKER_RECOVERY_TTL_SECONDS (default 300 seconds).

Recovery is bounded and observable. A recovery event is printed as JSON.
