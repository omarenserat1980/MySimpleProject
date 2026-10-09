# Brain Runtime Doctor

Run:

    python3 tools/brain_runtime_doctor.py

The doctor checks the local Python runtime, repository foundation, pytest,
SQLite persistence, and the independent gate.

It reports READY only when the local Brain execution path is actually usable.

It does not require GitHub Actions, a self-hosted runner, Windows, or arkan.
