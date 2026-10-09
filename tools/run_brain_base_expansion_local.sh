#!/data/data/com.termux/files/usr/bin/bash
set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 1

export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
export BRAIN_LOCAL_WORKER_ROOT="${BRAIN_LOCAL_WORKER_ROOT:-$ROOT/brain6_artifacts/local_worker}"
export BRAIN_WORKER_ID="${BRAIN_WORKER_ID:-brain-local-01}"

mkdir -p "$BRAIN_LOCAL_WORKER_ROOT/queued" "$BRAIN_LOCAL_WORKER_ROOT/running" "$BRAIN_LOCAL_WORKER_ROOT/completed" "$BRAIN_LOCAL_WORKER_ROOT/failed"

JOB_ID="base-expansion-integrity-$(date +%s)"
JOB="$BRAIN_LOCAL_WORKER_ROOT/queued/$JOB_ID.json"

python - "$JOB" "$JOB_ID" <<'PY'
import json, sys
path, job_id = sys.argv[1], sys.argv[2]
with open(path, "w", encoding="utf-8") as f:
    json.dump({"job_id": job_id, "task": "brain_base_expansion_integrity", "params": {}}, f, indent=2)
print(job_id)
PY

echo "BRAIN_JOB=$JOB_ID"
echo "Waiting for Brain Local Worker..."

for i in $(seq 1 3600); do
  if [ -f "$BRAIN_LOCAL_WORKER_ROOT/completed/$JOB_ID.json" ]; then
    cat "$BRAIN_LOCAL_WORKER_ROOT/completed/$JOB_ID.json"
    echo
    echo "BRAIN_EXECUTION=COMPLETED"
    exit 0
  fi
  if [ -f "$BRAIN_LOCAL_WORKER_ROOT/failed/$JOB_ID.json" ]; then
    cat "$BRAIN_LOCAL_WORKER_ROOT/failed/$JOB_ID.json"
    echo
    echo "BRAIN_EXECUTION=FAILED"
    exit 1
  fi
  sleep 1
done

echo "BRAIN_EXECUTION=TIMEOUT"
exit 2
