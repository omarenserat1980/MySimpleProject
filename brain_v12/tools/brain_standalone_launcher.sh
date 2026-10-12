#!/usr/bin/env bash
# Device-independent Electronic Brain runtime entrypoint.
# This starts Brain from the checked-out source and persistent runtime state.
# It intentionally does not inspect hardware, require an agent ID/key, contact
# GitHub to synchronize source, or start/require any emulator or remote device.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

PYTHON="${BRAIN_PYTHON:-$(command -v python3 || command -v python || true)}"
if [ -z "$PYTHON" ]; then
  echo "BRAIN_STANDALONE_ERROR=PYTHON_NOT_FOUND" >&2
  exit 42
fi

# Keep writable state independent of the source checkout. Explicit overrides
# remain supported. The app's runtime_paths module performs safe one-time
# migration of legacy state without deleting the original files.
export BRAIN_RUNTIME_HOME="${BRAIN_RUNTIME_HOME:-$HOME/.brain/runtime}"
export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"
export BRAIN_STANDALONE_MODE=1
HOST="${BRAIN_HOST:-127.0.0.1}"
PORT="${PORT:-8012}"

mkdir -p "$BRAIN_RUNTIME_HOME"
echo "BRAIN_STANDALONE_MODE=1"
echo "BRAIN_RUNTIME_HOME=$BRAIN_RUNTIME_HOME"
echo "BRAIN_LISTEN_ADDRESS=$HOST:$PORT"
exec "$PYTHON" -m uvicorn brain_v12.mcp_server:app --host "$HOST" --port "$PORT"
