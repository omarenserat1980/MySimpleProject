#!/usr/bin/env sh
set -eu
export PYTHONPATH="/app"
export PORT="${PORT:-10000}"
exec uvicorn brain_v12.app:app --host 0.0.0.0 --port "$PORT"
