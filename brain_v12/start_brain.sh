#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT/.."
# Load the local Brain↔Termux bridge secret when configured; never print it.
BRAIN_KEY_FILE="${BRAIN_EMULATOR_KEY_FILE:-${V12_AGENT_KEY_FILE:-$HOME/v12-agent/agent.key}}"
if [ -f "$BRAIN_KEY_FILE" ]; then
  export BRAIN_EMULATOR_KEY="$(cat "$BRAIN_KEY_FILE")"
fi
export PYTHONPATH="$PWD"
PORT="${PORT:-8012}"
if command -v curl >/dev/null 2>&1 && curl -fsS "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
  echo "Brain V12 already running on http://127.0.0.1:$PORT"
  exit 0
fi
python3 -m uvicorn brain_v12.mcp_server:app --host 0.0.0.0 --port "$PORT"
