#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

if [ -f "$HOME/.brain_env" ]; then . "$HOME/.brain_env"; fi
if [ -f "$HOME/v12-agent/agent_config.sh" ]; then . "$HOME/v12-agent/agent_config.sh"; fi

export V12_BRAIN_URL="${V12_BRAIN_URL:-http://127.0.0.1:8012}"
export V12_AGENT_ID="${V12_AGENT_ID:-redmi3-01}"
export V12_AGENT_KEY_FILE="${V12_AGENT_KEY_FILE:-$HOME/v12-agent/agent.key}"
export PYTHONPATH="$ROOT:${PYTHONPATH:-}"

PYTHON="${V12_PYTHON_EXECUTABLE:-$(command -v python3 || command -v python)}"
if [ -z "$PYTHON" ]; then
  echo "BRAIN_RUNTIME_ERROR: PYTHON_NOT_FOUND" >&2
  exit 42
fi

exec "$PYTHON" "$ROOT/brain_v12/tools/brain_emulator_agent.py"
