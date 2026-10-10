# Brain Execution Lease — additional initial piece

The initial lease contract models a bounded task lease with an executor identity,
expiry, and fencing token. It is intended as a future building block for distributed
workers to reduce stale-worker writes.

This is an in-memory value object only: no durable token allocation, atomic claim,
heartbeat renewal, distributed locking, or executor integration is implemented.
It does not prove that a worker owns a real task.

Initial tests:

    PYTHONPATH=. python -m pytest -q brain_v12/tests/test_execution_lease.py
