#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT:${PYTHONPATH:-}"

echo "===== BRAIN INDEPENDENCE PROOF ====="
python tools/brain_independence_proof_gate.py

echo
echo "===== BRAIN EXECUTOR HEARTBEAT ====="
python - <<'PY'
from platform_foundation.brain_execution_authority import BrainExecutionAuthority
import json
print(json.dumps(BrainExecutionAuthority().heartbeat(), indent=2, ensure_ascii=False))
PY

echo
echo "===== LIVE AUTONOMY GATE ====="
python tools/brain_autonomy_gate.py

echo
echo "BRAIN_LIVE_AUTONOMY=PROVEN_WITHIN_AUTHORITY"
