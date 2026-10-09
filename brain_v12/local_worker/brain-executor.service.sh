#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
export BRAIN_WORKER_ID="${BRAIN_WORKER_ID:-brain-local-01}"
export BRAIN_LOCAL_WORKER_ROOT="${BRAIN_LOCAL_WORKER_ROOT:-$ROOT/brain6_artifacts/local_worker}"
export BRAIN_EXECUTOR_HEARTBEAT="${BRAIN_EXECUTOR_HEARTBEAT:-$BRAIN_LOCAL_WORKER_ROOT/heartbeat.json}"

cd "$ROOT"
exec python3 brain_v12/local_worker/bootstrap_brain_executor.py
