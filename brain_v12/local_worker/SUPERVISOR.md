# Brain Local Worker Supervisor

Start:

    python3 brain_v12/local_worker/brain_local_supervisor.py

Check:

    python3 brain_v12/local_worker/check_supervisor.py

The supervisor restarts the Brain Local Worker when it exits and persists
heartbeat/restart state in:

    brain6_artifacts/local_worker/supervisor.json

The supervisor is Brain-local and does not require Windows, arkan, or GitHub
Actions.
