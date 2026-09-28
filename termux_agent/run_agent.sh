#!/usr/bin/env bash
set -euo pipefail

: "${BRAIN_URL:?BRAIN_URL is required}"
: "${BRAIN_EMULATOR_KEY:?BRAIN_EMULATOR_KEY is required}"

export BRAIN_EMULATOR_ID="${BRAIN_EMULATOR_ID:-android-brain-emulator-v12}"
export BRAIN_EMULATOR_POLL_SECONDS="${BRAIN_EMULATOR_POLL_SECONDS:-2}"
export BRAIN_EMULATOR_MAX_TASKS_PER_RUN="${BRAIN_EMULATOR_MAX_TASKS_PER_RUN:-100}"
export BRAIN_EMULATOR_HEARTBEAT_SECONDS="${BRAIN_EMULATOR_HEARTBEAT_SECONDS:-10}"
export BRAIN_EMULATOR_REQUEST_TIMEOUT="${BRAIN_EMULATOR_REQUEST_TIMEOUT:-30}"

echo "[V12-Agent] preflight"
python --version
echo "[V12-Agent] Brain: $BRAIN_URL"
echo "[V12-Agent] Agent: $BRAIN_EMULATOR_ID"
echo "[V12-Agent] starting gateway agent"

exec python termux_agent/v12_agent.py
