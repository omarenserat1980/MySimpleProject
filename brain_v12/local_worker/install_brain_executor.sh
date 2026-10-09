#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

export BRAIN_WORKER_ID="${BRAIN_WORKER_ID:-brain-local-01}"
export BRAIN_LOCAL_WORKER_ROOT="${BRAIN_LOCAL_WORKER_ROOT:-$ROOT/brain6_artifacts/local_worker}"
export BRAIN_EXECUTOR_HEARTBEAT="${BRAIN_EXECUTOR_HEARTBEAT:-$BRAIN_LOCAL_WORKER_ROOT/heartbeat.json}"

mkdir -p "$BRAIN_LOCAL_WORKER_ROOT"/{queued,running,completed,failed}
python3 -m pytest -q tests/test_brain_execution_authority.py tests/test_local_worker_authority.py tests/test_brain_executor_bootstrap.py

echo "BRAIN_EXECUTOR_INSTALL_VERIFIED"
echo "worker_id=$BRAIN_WORKER_ID"
echo "heartbeat=$BRAIN_EXECUTOR_HEARTBEAT"
echo "runner_policy=BRAIN_ONLY"
echo "github_hosted_fallback=FORBIDDEN"

exec python3 brain_v12/local_worker/bootstrap_brain_executor.py
