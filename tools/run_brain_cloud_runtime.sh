#!/usr/bin/env bash
set -euo pipefail

export BRAIN_INTERNAL_RUNNER_FLAG=1
export BRAIN_RUNTIME_ROOT="${BRAIN_RUNTIME_ROOT:-/var/lib/brain/runtime}"
export BRAIN_WORKER_POLL_SECONDS="${BRAIN_WORKER_POLL_SECONDS:-2}"
export BRAIN_TASK_TIMEOUT="${BRAIN_TASK_TIMEOUT:-3600}"

exec python -m brain_v12.cloud_runtime.worker
