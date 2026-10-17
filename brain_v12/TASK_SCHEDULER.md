# Brain Task Scheduler — Piece 4

Initial policy-only skeleton. It selects a suitable record from an explicitly
provided resource list using a deterministic best-fit ordering.

This is not a task executor: it does not launch work, allocate capacity, claim
leases, provision cloud resources, or contact devices. Unknown capacity is not
treated as available. The selection result explicitly says it was not executed.

Run the initial tests from the repository root:

    PYTHONPATH=. python -m pytest -q brain_v12/tests/test_task_scheduler.py
