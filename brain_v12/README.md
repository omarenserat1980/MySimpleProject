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

## Human Presence Avatar

A zero-dependency Arabic RTL avatar prototype is available at `web/brain-avatar/index.html`.
When served by the Brain FastAPI app, open `/brain-avatar/`. The page polls
`/api/brain-avatar/state` every five seconds while live sync is enabled. This endpoint reads
liveness and recent runtime events and may also persist a bounded `HUMAN_PRESENCE` pulse tick
through Brain's existing `MemoryStore` (at most one tick per minute); it is therefore not strictly
read-only. It never triggers device execution. The avatar is a UI representation, not evidence of
subjective feelings or consciousness; no camera, microphone, face recognition, or external service
is used. The API reports `PENDING_RENDER_CONFIRMATION`; this does not prove the browser rendered a
frame or establish an always-on background heartbeat. Turning off live sync stops further UI polls.

Contract tests:
`python -m unittest brain_v12.tests.test_brain_avatar_contract -v`
