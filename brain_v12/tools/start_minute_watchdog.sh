#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
mkdir -p brain6_artifacts/workflow_watchdog
export BRAIN_GITHUB_REPO="${BRAIN_GITHUB_REPO:-omarenserat1980/MySimpleProject}"
export BRAIN_WATCHDOG_SECONDS="${BRAIN_WATCHDOG_SECONDS:-120}"
export BRAIN_WATCHDOG_MAX_ATTEMPTS="${BRAIN_WATCHDOG_MAX_ATTEMPTS:-3}"
nohup python -m brain_v12.brain.brain_minute_watchdog \
  >> brain6_artifacts/workflow_watchdog/minute-watchdog.stdout.log 2>&1 &
echo $! > brain6_artifacts/workflow_watchdog/minute-watchdog.pid
echo "BRAIN_MINUTE_WATCHDOG=STARTED"
echo "PID=$(cat brain6_artifacts/workflow_watchdog/minute-watchdog.pid)"
echo "INTERVAL=${BRAIN_WATCHDOG_SECONDS}s"
