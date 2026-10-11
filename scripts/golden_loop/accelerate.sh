#!/usr/bin/env bash
# Fast, read-only Golden Loop triage. Exit 2 means evidence is still blocked.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
EVIDENCE_ROOT="${1:-$REPO_ROOT/brain6_artifacts}"
EXPECTED_RUN_ID="${2:-}"
REPORT="$EVIDENCE_ROOT/golden-loop-accelerator-report.json"

cd "$REPO_ROOT"
python3 -m unittest brain_v12.tests.test_golden_loop_accelerator -v

args=(--root "$EVIDENCE_ROOT" --output "$REPORT")
if [[ -n "$EXPECTED_RUN_ID" ]]; then
  args+=(--expected-run-id "$EXPECTED_RUN_ID")
fi

set +e
python3 -m brain_v12.tools.golden_loop_accelerator "${args[@]}"
rc=$?
set -e
if [[ "$rc" -eq 2 ]]; then
  printf 'GOLDEN_LOOP_BLOCKED=1\nREPORT=%s\n' "$REPORT"
elif [[ "$rc" -eq 0 ]]; then
  printf 'GOLDEN_LOOP_VERIFIED=1\nREPORT=%s\n' "$REPORT"
else
  printf 'GOLDEN_LOOP_TRIAGE_ERROR=%s\n' "$rc" >&2
fi
exit "$rc"
