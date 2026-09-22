# Electronic Brain V12

Clean reconstruction of the accumulated Electronic Brain architecture.

Core loop:
Perceive -> Understand -> Memory -> Goal -> Plan -> Decide -> Act -> Observe -> Error -> Learn -> Memory.

The core never pretends an external action happened. Device execution is isolated behind the Agent Bridge and explicit permissions.

Components:
- app.py: FastAPI control plane and UI
- brain/core.py: cognitive state machine
- brain/memory.py: SQLite memory and events
- brain/planner.py: planning and option scoring
- brain/agent.py: bounded local-agent bridge
- brain/builder.py: software-builder planning loop
- web/index.html: main control interface

Run:
python -m brain_v12.app

Default: http://127.0.0.1:8012
