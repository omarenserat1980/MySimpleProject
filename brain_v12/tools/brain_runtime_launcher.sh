#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

if [ -f "$HOME/.brain_env" ]; then . "$HOME/.brain_env"; fi
if [ -f "$HOME/v12-agent/agent_config.sh" ]; then . "$HOME/v12-agent/agent_config.sh"; fi

# Render is intentionally not part of the Jet Brain runtime.
if [[ "${BRAIN_URL:-}" == *render.com* ]]; then unset BRAIN_URL; fi
if [[ "${V12_BRAIN_URL:-}" == *render.com* ]]; then unset V12_BRAIN_URL; fi

export V12_BRAIN_URL="${BRAIN_URL:-http://127.0.0.1:8012}"
export V12_AGENT_ID="${V12_AGENT_ID:-redmi3-01}"
export V12_AGENT_KEY_FILE="${V12_AGENT_KEY_FILE:-$HOME/v12-agent/agent.key}"
export BRAIN_AGENT_KEY_FILE="${V12_AGENT_KEY_FILE}"
export PYTHONPATH="$ROOT:${PYTHONPATH:-}"

PYTHON="${V12_PYTHON_EXECUTABLE:-$(command -v python3 || command -v python)}"
if [ -z "$PYTHON" ]; then echo "BRAIN_RUNTIME_ERROR: PYTHON_NOT_FOUND" >&2; exit 42; fi

# One-command local runtime: start Brain API if it is not already healthy.
if ! "$PYTHON" -c 'import os,urllib.request; urllib.request.urlopen(os.environ["V12_BRAIN_URL"]+"/health",timeout=2).read()' >/dev/null 2>&1; then
  echo "JET_BRAIN_API starting url=$V12_BRAIN_URL" >&2
  "$PYTHON" -m uvicorn brain_v12.app:app --host 127.0.0.1 --port 8012 --workers 1 --log-level warning >> "$ROOT/.brain/state/api.log" 2>&1 &
  API_PID=$!
  for i in $(seq 1 20); do
    if "$PYTHON" -c 'import os,urllib.request; urllib.request.urlopen(os.environ["V12_BRAIN_URL"]+"/health",timeout=2).read()' >/dev/null 2>&1; then break; fi
    sleep 1
  done
  if ! "$PYTHON" -c 'import os,urllib.request; urllib.request.urlopen(os.environ["V12_BRAIN_URL"]+"/health",timeout=2).read()' >/dev/null 2>&1; then
    echo "BRAIN_RUNTIME_ERROR: API_START_FAILED pid=$API_PID" >&2
    exit 43
  fi
  echo "JET_BRAIN_API ready pid=$API_PID" >&2
else
  echo "JET_BRAIN_API already_ready url=$V12_BRAIN_URL" >&2
fi

echo "JET_BRAIN_RUNTIME url=$V12_BRAIN_URL agent=$V12_AGENT_ID" >&2
exec "$PYTHON" "$ROOT/brain_v12/tools/brain_emulator_agent.py"
