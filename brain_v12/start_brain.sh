#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT/.."
export PYTHONPATH="$PWD"
PORT="${PORT:-8012}"
if command -v curl >/dev/null 2>&1 && curl -fsS "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
  echo "Brain V12 already running on http://127.0.0.1:$PORT"
  exit 0
fi
python3 -m uvicorn brain_v12.app:app --host 0.0.0.0 --port "$PORT"
