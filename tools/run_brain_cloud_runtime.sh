#!/usr/bin/env bash
set -euo pipefail

# Trust identity must be provisioned by the authorized host/service configuration.
# This launcher must never self-assert that the current host is trusted.
: "${BRAIN_INTERNAL_RUNNER_FLAG:?Set BRAIN_INTERNAL_RUNNER_FLAG in the authorized host environment}"
if [[ "$BRAIN_INTERNAL_RUNNER_FLAG" != "1" ]]; then
  echo "BRAIN_INTERNAL_RUNNER_FLAG_INVALID" >&2
  exit 24
fi

export BRAIN_RUNTIME_ROOT="${BRAIN_RUNTIME_ROOT:-/var/lib/brain/runtime}"
export BRAIN_WORKER_POLL_SECONDS="${BRAIN_WORKER_POLL_SECONDS:-2}"
export BRAIN_TASK_TIMEOUT="${BRAIN_TASK_TIMEOUT:-3600}"

exec python -m brain_v12.cloud_runtime.worker
