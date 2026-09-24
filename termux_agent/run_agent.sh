#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

: "${BRAIN_URL:?BRAIN_URL is required}"
: "${TERMUX_AGENT_KEY:?TERMUX_AGENT_KEY is required}"

export TERMUX_AGENT_ID="${TERMUX_AGENT_ID:-android-termux-v12}"
export TERMUX_POLL_SECONDS="${TERMUX_POLL_SECONDS:-2}"
export TERMUX_MAX_TASKS_PER_RUN="${TERMUX_MAX_TASKS_PER_RUN:-100}"
export TERMUX_HEARTBEAT_SECONDS="${TERMUX_HEARTBEAT_SECONDS:-10}"

echo "[V12-Agent] preflight"
python --version
echo "[V12-Agent] Brain: $BRAIN_URL"
echo "[V12-Agent] Agent: $TERMUX_AGENT_ID"
echo "[V12-Agent] starting gateway agent"

exec python termux_agent/v12_agent.py
