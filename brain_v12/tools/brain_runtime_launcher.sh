#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

if [ -f "$HOME/.brain_env" ]; then . "$HOME/.brain_env"; fi
if [ -f "$HOME/v12-agent/agent_config.sh" ]; then . "$HOME/v12-agent/agent_config.sh"; fi

# Render is intentionally not part of the Jet Brain runtime.
if [ -n "${BRAIN_URL:-}" ] && [[ "${BRAIN_URL}" == *render.com* ]]; then unset BRAIN_URL; fi
if [ -n "${V12_BRAIN_URL:-}" ] && [[ "${V12_BRAIN_URL}" == *render.com* ]]; then unset V12_BRAIN_URL; fi
export V12_BRAIN_URL="${BRAIN_URL:-http://127.0.0.1:8012}"
export V12_AGENT_ID="${V12_AGENT_ID:-redmi3-01}"
export V12_AGENT_KEY_FILE="${V12_AGENT_KEY_FILE:-$HOME/v12-agent/agent.key}"
export PYTHONPATH="$ROOT:${PYTHONPATH:-}"

PYTHON="${V12_PYTHON_EXECUTABLE:-$(command -v python3 || command -v python)}"
if [ -z "$PYTHON" ]; then echo "BRAIN_RUNTIME_ERROR: PYTHON_NOT_FOUND" >&2; exit 42; fi
echo "JET_BRAIN_RUNTIME url=$V12_BRAIN_URL agent=$V12_AGENT_ID" >&2
exec "$PYTHON" "$ROOT/brain_v12/tools/brain_emulator_agent.py"
