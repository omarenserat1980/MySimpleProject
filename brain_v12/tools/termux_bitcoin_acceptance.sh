#!/data/data/com.termux/files/usr/bin/bash
# Electronic Brain: Termux Bitcoin SHA-256d acceptance preflight.
# Safe by default: this script does NOT start mining or contact a pool.
set -u
ROOT="${BRAIN_REPO_ROOT:-$HOME/MySimpleProject}"
OUT="${BRAIN_MINING_EVIDENCE_DIR:-$HOME/brain-mining-evidence}"
mkdir -p "$OUT"
REPORT="$OUT/termux-preflight-$(date -u +%Y%m%dT%H%M%SZ).txt"
exec > >(tee "$REPORT") 2>&1

echo "component=electronic-brain-termux-bitcoin-preflight"
echo "timestamp_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "device_arch=$(uname -m 2>/dev/null || echo unknown)"
echo "android_abis=$(getprop ro.product.cpu.abilist 2>/dev/null || echo unavailable)"
echo "termux_version=${TERMUX_VERSION:-unset}"
echo "python=$(python --version 2>&1 || true)"
echo "git=$(git --version 2>&1 || true)"
echo "clang=$(clang --version 2>/dev/null | head -n 1 || echo unavailable)"
echo "make=$(make --version 2>/dev/null | head -n 1 || echo unavailable)"
echo "cpuminer_path=$(command -v cpuminer || echo not-installed)"

if [ ! -d "$ROOT/.git" ]; then
  echo "status=BLOCKED_REPOSITORY_NOT_FOUND"
  echo "expected_repo=$ROOT"
  echo "No mining process started."
  exit 2
fi

cd "$ROOT" || exit 2
echo "repo_root=$ROOT"
echo "git_branch=$(git branch --show-current)"
echo "git_commit=$(git rev-parse HEAD)"
echo "git_worktree_status_begin"
git status --short
echo "git_worktree_status_end"

if ! python -c 'import brain_v12.brain.termux_bitcoin_worker' >/dev/null 2>&1; then
  echo "status=BLOCKED_WORKER_IMPORT_FAILED"
  echo "No mining process started."
  exit 2
fi

echo "unit_tests_begin"
if python -m unittest brain_v12.tests.test_termux_bitcoin_worker -v; then
  echo "unit_tests=PASS"
else
  echo "unit_tests=FAIL"
  echo "No mining process started."
  exit 1
fi
echo "unit_tests_end"

if command -v cpuminer >/dev/null 2>&1; then
  echo "miner_version_begin"
  cpuminer --version 2>&1 | head -n 8 || true
  echo "miner_version_end"
  echo "miner_algorithm_support=UNVERIFIED; inspect this binary's help/version and verify SHA-256d support before use"
else
  echo "miner_status=NOT_INSTALLED"
fi

echo "status=PREFLIGHT_COMPLETE_NOT_MINING"
echo "pool_session_verified=false"
echo "pool_side_hashrate_verified=false"
echo "accepted_shares_verified=false"
echo "revenue_verified=false"
echo "evidence_report=$REPORT"
echo "Next: verify a trusted Android/Termux-compatible miner binary and pool endpoint manually; do not place pool passwords or wallet secrets in this report."
