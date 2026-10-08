# Brain Termux Operations

## Confirmed project path
/data/data/com.termux/files/home/MySimpleProject
Termux shorthand: ~/MySimpleProject

## Runtime scripts
- brain_v12/tools/brain_runtime_bootstrap.sh
- brain_v12/tools/brain_runtime_launcher.sh
- brain_v12/tools/brain_runtime_supervisor.py
- brain_v12/tools/brain_emulator_agent.py
- brain_v12/tools/brain_runtime_source_manager.sh

## Runtime state
~/MySimpleProject/.brain/state

Known operational files:
- api.log
- supervisor.log
- supervisor.pid
- continuous_supervisor.jsonl
- continuous_tasks.jsonl
- continuous_supervisor.lock
- runtime-bootstrap.log
- runtime-bootstrap.pid
- sync_queue.jsonl

## Agent configuration
File: ~/v12-agent/agent_config.sh

Confirmed non-secret values:
- V12_AGENT_ID=redmi3-01
- V12_AGENT_KEY_FILE=$HOME/v12-agent/agent.key
- V12_BRAIN_URL=http://127.0.0.1:8012

Secret material:
- ~/v12-agent/agent.key
- ~/.brain_env
Secret values are never documented or committed.

## Runtime contract
- API: 127.0.0.1:8012
- Uvicorn workers: 1
- Supervisor: single-instance lock
- Default supervisor interval: 60 seconds
- Minimum supervisor interval: 15 seconds

## Recovery rule
A replacement phone must obtain source/config from the canonical recovery path and must not depend on the old phone filesystem.
